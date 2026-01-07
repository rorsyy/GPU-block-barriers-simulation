import sys
import os
import time
import threading
import urllib.request
import urllib.error

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from controller.simulation_controller import SimulationController

def run_test():
    print("Starting In-Process Server for Frontend Test...")
    
    config_path = "config/default_scenario.json"
    if not os.path.exists(config_path):
        config_path = r"d:\code\GPU_barrier_similation\config\default_scenario.json"
    
    controller = SimulationController(config_path)
    t = threading.Thread(target=controller.start)
    t.daemon = True
    t.start()
    
    time.sleep(2)
    base_url = "http://localhost:8000"
    
    try:
        # 1. Test Static File Serving (Index)
        print("Test: Fetching / (index.html)...")
        with urllib.request.urlopen(f"{base_url}/") as f:
            content = f.read().decode('utf-8')
            if "<title>GPU Barrier Simulation</title>" in content:
                print("PASS: index.html served correctly")
            else:
                print("FAIL: index.html content mismatch")

        # 2. Test Static File Serving (JS)
        print("Test: Fetching /app.js...")
        with urllib.request.urlopen(f"{base_url}/app.js") as f:
            content = f.read().decode('utf-8')
            if "const API_BASE" in content:
                print("PASS: app.js served correctly")
            else:
                print("FAIL: app.js content mismatch")

        # 3. Test API still works
        print("Test: Fetching /api/state...")
        with urllib.request.urlopen(f"{base_url}/api/state") as f:
            if f.status == 200:
                print("PASS: API endpoint works")
            else:
                print(f"FAIL: API returned status {f.status}")

    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        print("Stopping Controller...")
        controller.running = False
        controller.api_server.running = False

if __name__ == "__main__":
    run_test()
