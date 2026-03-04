from flask import Flask
from flask_cors import CORS
from threading import Thread
import time
import random

class MockCollector:
    def __init__(self):
        self.running = True
        self.data = []
        self.start_time = time.time()
        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']

    def run(self):
        """Simulates data collection loop."""
        print("Mock Collector thread started.")
        while self.running:
            # Simulate a recording cycle (like the PLC trigger)
            # In mock mode, we'll just constantly generate some data
            elapsed_ms = (time.time() - self.start_time) * 1000
            
            # Generate 7 mock register values
            # TCP values usually oscillate or stay within ranges
            line = [
                elapsed_ms,
                500 + 10 * random.uniform(-1, 1), # TCP_x
                -200 + 10 * random.uniform(-1, 1), # TCP_y
                600 + 10 * random.uniform(-1, 1), # TCP_z
                3.14 + 0.1 * random.uniform(-1, 1), # TCP_rx
                0.0 + 0.1 * random.uniform(-1, 1), # TCP_ry
                1.57 + 0.1 * random.uniform(-1, 1), # TCP_rz
                2.5 + 0.5 * random.uniform(-1, 1)   # Robot_I
            ]
            
            self.data.append(line)
            
            # Keep only the last 100 points to prevent memory bloat, 
            # similar to how a real-time monitor might behave
            if len(self.data) > 100:
                self.data.pop(0)
                
            time.sleep(0.1) # 10Hz data rate

    def stop(self):
        self.running = False

app = Flask(__name__)
CORS(app)

# Initialize the collector globally so routes can access it
w = MockCollector()

@app.route('/')
def index():
    return "Mock API is running"

@app.route('/data')
def get_data():
    return {"data": w.data}

def main():
    # Start the mock data generation thread
    thread = Thread(target=w.run)
    thread.daemon = True
    thread.start()
    
    print("Starting mock server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
