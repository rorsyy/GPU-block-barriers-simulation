import sys
import os
import json
import threading
import time

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from controller.simulation_controller import SimulationController
from model.simulation_model import SimulationState

def test_reset_logic():
    print("Testing SimulationController RESET logic...")
    
    # Path to config
    config_path = "config/default_scenario.json"
    
    # Init controller
    controller = SimulationController(config_path)
    
    # Check initial barrier type
    initial_type = controller.model.barrier.get_status()["type"]
    print(f"Initial Barrier Type: {initial_type}")
    
    if initial_type != "CENTRALIZED":
        print("WARNING: Default is not CENTRALIZED?")

    # Simulate RESET command
    msg = {
        "command": "RESET",
        "config": {"barrier_type": "TREE"}
    }
    
    print(f"Sending RESET with {msg['config']}")
    controller.command_queue.put(msg)
    
    # Run loop for a short time to process command
    # We can't call run_loop directly as it blocks.
    # We can start it in a thread, or just call _handle_command directly for unit testing.
    
    print("Directly calling _handle_command to avoid threading complexity in test...")
    controller._handle_command(msg)
    
    # Check new barrier type
    new_type = controller.model.barrier.get_status()["type"]
    print(f"New Barrier Type: {new_type}")
    
    if new_type == "TREE":
        print("PASS: Barrier switched to TREE")
    else:
        print(f"FAIL: Expected TREE, got {new_type}")
        print(f"Controller Config Settings: {controller.config.get('settings')}")

    # Clean up
    controller.running = False
    controller.api_server.running = False
    # controller.api_server.join() # It's a daemon

if __name__ == "__main__":
    test_reset_logic()
