import sys
import random
import time
import os
from unittest.mock import MagicMock

# --- 1. Define the "Muck" Clients ---

class Snap7MuckClient:
    """Mocks snap7.client.Client"""
    def connect(self, ip, rack, slot):
        print(f"[Muck] Mocking PLC connection to {ip}...")
        return None
    
    def db_read(self, db_number, start, size):
        # Returns a bytearray. Bit 0 of the first byte is the signal.
        # We'll randomly flip it to simulate the PLC turning on and off.
        # 1 means START recording, 0 means STOP.
        signal = 1 if random.random() > 0.5 else 0
        return bytearray([signal])

class ModbusMuckClient:
    """Mocks pyModbusTCP.client.ModbusClient"""
    def __init__(self, host=None, port=None, auto_open=True):
        self.host = host
        self.port = port
        print(f"[Muck] Mocking Modbus connection to {host}...")

    def read_holding_registers(self, reg_addr, count=1):
        # Returns a list of integers. 
        # main.py does reg[0] = result, then later reg[0][0]
        # So we must return [value]
        return [random.randint(100, 5000)]

# --- 2. Inject Mocks into sys.modules BEFORE importing main ---

# Mock snap7 module
mock_snap7 = MagicMock()
mock_snap7.client.Client = Snap7MuckClient
# Keep the real utility function because main.py uses it for logic
import snap7.util
mock_snap7.util = snap7.util
sys.modules['snap7'] = mock_snap7

# Mock pyModbusTCP module
mock_modbus_pkg = MagicMock()
mock_modbus_client_mod = MagicMock()
mock_modbus_client_mod.ModbusClient = ModbusMuckClient
sys.modules['pyModbusTCP'] = mock_modbus_pkg
sys.modules['pyModbusTCP.client'] = mock_modbus_client_mod

# --- 3. Now Import Main ---

import pandas as pd
# Fix for newer pandas versions where applymap was renamed to map
if not hasattr(pd.DataFrame, 'applymap'):
    pd.DataFrame.applymap = pd.DataFrame.map

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

import main
from threading import Thread

# Since main.py creates 'w' inside its main() function, 
# we need to create it manually here and attach it to the module.
print("[Test] Manually instantiating 'w' for the module...")
main.w = main.collector()

# Pre-fill registers with [0] instead of 0 so reg[0][0] doesn't crash 
# before the first mock read happens.
for reg in main.w.registers:
    reg[0] = [0]

Thread(target=main.w.run, daemon=True).start()
Thread(target=main.w.plc_run, daemon=True).start()

# --- 4. The Test Script ---

def run_offline_test():
    print("\n" + "="*40)
    print("OFFLINE TEST STARTED (All hardware mocked)")
    print("="*40)

    # Use Flask's test client
    client = main.app.test_client()

    try:
        # Run for a few seconds to let the background threads gather "garbage"
        for i in range(10):
            count = len(main.w.data)
            print(f"Time: {i}s | Data points in memory: {count}")
            
            # Test Flask API while it's running
            res = client.get('/data')
            if res.status_code == 200:
                json_data = res.get_json()
                if json_data['data']:
                    print(f"  -> Latest garbage sample (len {len(json_data['data'][-1])}): {json_data['data'][-1]}")
            
            time.sleep(1)

        print("\nTesting / endpoint...")
        index_res = client.get('/')
        print(f"Status: {index_res.status_code}, Body: {index_res.data.decode()}")

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down threads...")
        main.w.stop()
        print("Done.")

if __name__ == "__main__":
    run_offline_test()
