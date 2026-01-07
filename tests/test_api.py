import sys
import os
import json
import time
import threading
import urllib.request
import urllib.error

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from controller.simulation_controller import SimulationController

def run_test():
    print("Starting In-Process Test Server...")
    
    # Path to config
    # Try different paths
    config_path = "config/default_scenario.json"
    if not os.path.exists(config_path):
        config_path = r"d:\code\GPU_barrier_similation\config\default_scenario.json"
    
    # Init controller
    controller = SimulationController(config_path)
    
    # Start controller loop in a thread
    t = threading.Thread(target=controller.start)
    t.daemon = True
    t.start()
    
    # Wait for server start
    time.sleep(2)
    
    base_url = "http://localhost:8000/api"
    
    try:
        # 1. Test Start
        print("Test: Sending START command...")
        req = urllib.request.Request(f"{base_url}/control", 
            data=json.dumps({"command": "START"}).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req) as f:
            print(f"Response: {f.read().decode('utf-8')}")

        time.sleep(1)
        
        # 2. Test State Query (Default Centralized)
        print("Test: Query State...")
        with urllib.request.urlopen(f"{base_url}/state") as f:
            state = json.loads(f.read().decode('utf-8'))
            b_type = state['barrier'].get('type')
            print(f"State: Tick={state['tick']}, BarrierType={b_type}")
            if b_type == 'CENTRALIZED':
                print("PASS: Default is CENTRALIZED")
            else:
                 print(f"FAIL: Expected CENTRALIZED, got {b_type}")

        # 3. Test Reset to TREE
        print("Test: Reset to TREE Barrier...")
        req = urllib.request.Request(f"{base_url}/control", 
            data=json.dumps({
                "command": "RESET", 
                "config": {"barrier_type": "TREE"}
            }).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req) as f:
             print(f"Response: {f.read().decode('utf-8')}")
             
        # Need to START again
        req = urllib.request.Request(f"{base_url}/control", 
            data=json.dumps({"command": "START"}).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req) as f: pass

        time.sleep(1)
        
        # 4. Verify TREE
        print("Test: Query State (Expect TREE)...")
        with urllib.request.urlopen(f"{base_url}/state") as f:
            state = json.loads(f.read().decode('utf-8'))
            b_type = state['barrier'].get('type')
            print(f"State: Tick={state['tick']}, BarrierType={b_type}")
            if b_type == 'TREE':
                print("PASS: Barrier switched to TREE")
            else:
                print(f"FAIL: Expected TREE, got {b_type}")

    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        print("Stopping Contoller...")
        controller.running = False
        controller.api_server.running = False

if __name__ == "__main__":
    run_test()
