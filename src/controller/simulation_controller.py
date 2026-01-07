import time
import threading
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Queue, Empty
from model.simulation_model import SimulationModel, SimulationState
from utils.logger import SimulationLogger

# API Server Handler
class SimulationAPIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/control':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                # 将命令放入 controller 的队列
                self.server.controller.command_queue.put(data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            except Exception as e:
                self.send_error(400, f"Invalid JSON: {str(e)}")
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/api/state':
            snapshot = self.server.controller.current_snapshot
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(snapshot).encode('utf-8'))
        
        elif self.path == '/api/metrics':
            # 获取栅栏性能指标
            metrics = {}
            try:
                metrics = self.server.controller.model.get_barrier_metrics()
            except Exception as e:
                metrics = {"error": str(e)}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode('utf-8'))
        
        else:
            # Serve Static Files
            file_path = self.path
            if file_path == "/":
                file_path = "/index.html"
            
            # Map request path to local file path in src/web
            # Remove leading slash
            relative_path = file_path.lstrip("/")
            # Basic security: prevent directory traversal
            if ".." in relative_path:
                self.send_error(403)
                return

            # Construct full path
            # Assuming cwd is project root (d:\code\GPU_barrier_similation)
            # or src/controller's parent...
            # Best to use absolute path relative to src/web
            # self.server.controller.web_root should ideally be set, 
            # here we assume src/web is at os.getcwd()/src/web
            
            # Use os.getcwd() if running from root
            local_path = os.path.join(os.getcwd(), "src", "web", relative_path)
            
            if os.path.exists(local_path) and os.path.isfile(local_path):
                self.send_response(200)
                
                # Determine MIME type
                if local_path.endswith(".html"):
                    self.send_header('Content-type', 'text/html')
                elif local_path.endswith(".css"):
                    self.send_header('Content-type', 'text/css')
                elif local_path.endswith(".js"):
                    self.send_header('Content-type', 'application/javascript')
                else:
                     self.send_header('Content-type', 'application/octet-stream')
                     
                self.end_headers()
                
                with open(local_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {local_path}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()


class APIServerThread(threading.Thread):
    def __init__(self, controller, port=8000):
        super().__init__()
        self.controller = controller
        self.port = port
        self.httpd = HTTPServer(('localhost', port), SimulationAPIHandler)
        self.httpd.controller = controller # Bind controller to server
        self.running = True

    def run(self):
        print(f"API Server started on http://localhost:{self.port}")
        while self.running:
            self.httpd.handle_request()

    def stop(self):
        self.running = False
        # self.httpd.shutdown() # shutdown() might hang if no request comes, handle_request with timeout is better or just daemon
        # Simplification: let it die with daemon or explicit close logic


class SimulationController:
    """
    仿真控制器 (Controller)
    """
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.logger = SimulationLogger("trace.log")
        self.model = SimulationModel(logger=self.logger)
        self.model.init_simulation(self.config)
        
        self.view = None 
        self.running = True
        
        # Thread-safe Command Queue
        self.command_queue = Queue()
        
        # Shared state for API (read-only for API, write by main loop)
        self.current_snapshot = {}

        # Start API Server
        self.api_server = APIServerThread(self)
        self.api_server.daemon = True # Daemon thread exits when main thread exits
        self.api_server.start()

    def set_view(self, view):
        self.view = view

    def start(self):
        """启动主循环"""
        self.model.start()
        self.run_loop()

    def run_loop(self):
        """
        阻塞式主循环。
        """
        try:
            while self.running:
                # 1. Process External Commands
                try:
                    while not self.command_queue.empty():
                        cmd = self.command_queue.get_nowait()
                        self._handle_command(cmd)
                except Empty:
                    pass

                # 2. Simulation Logic
                if self.model.state == SimulationState.RUNNING:
                    self.model.step()
                    
                    if self.model.current_tick % 10 == 0: 
                        self.logger.log_event("SNAPSHOT", {"active_blocks": len([b for b in self.model.blocks if b.state.name == 'RUNNING'])})

                    if self.model.state == SimulationState.COMPLETED:
                        print("Simulation Completed.")
                        # Auto-pause at completion
                        self.model.state = SimulationState.STOPPED

                elif self.model.state == SimulationState.PAUSED:
                    time.sleep(0.1)
                
                # 3. Update State Snapshot for API and View
                self.current_snapshot = self.model.get_snapshot()

                # 4. View Render
                if self.view:
                    self.view.render(self.current_snapshot)
                
                # 5. Rate Limit
                time.sleep(0.05) 
                
        except KeyboardInterrupt:
            print("Stopping by User...")
        finally:
            self.logger.close()
            # API server is daemon, will die
            
    def _handle_command(self, cmd):
        """Handle commands from API"""
        action = cmd.get("command")
        print(f"Received Command: {action}")
        
        if action == "START":
            self.model.state = SimulationState.RUNNING
        elif action == "PAUSE":
            self.model.pause()
        elif action == "STEP":
            if self.model.state != SimulationState.RUNNING: # Only step when not running freely? Or force step?
                # Force single step
                self.model.state = SimulationState.RUNNING # Temporarily run
                self.model.step()
                self.model.state = SimulationState.PAUSED
        elif action == "RESET":
            # Reload config if provided
            new_config = cmd.get("config")
            if new_config:
                # Merge or replace settings
                self.config["settings"].update(new_config)
            print(f"RESET Config Settings: {self.config.get('settings')}")
            self.model.init_simulation(self.config)
            print("Simulation Reset.")
