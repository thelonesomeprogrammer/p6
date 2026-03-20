from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from threading import Thread
import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
import os
import time
import snap7
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import xml.etree.ElementTree as ET


class KXMLHandler(FileSystemEventHandler):
    def __init__(self, collector):
        self.collector = collector

    def on_created(self, event):
        if event.src_path.endswith('.kxml'):
            self.collector.kxml_ingest(event.src_path)


class collector():
    def __init__(self, client=None, c=None):
        self.running = True

        self.today = datetime.today().strftime('%d%m%Y')

        ## PLC connection
        self.client = client if client else snap7.client.Client()
        self.client.connect('172.20.1.148', 0, 1)
        self.db_number = 19
        self.start_offset = 0
        self.bit_offset = 0

        ## Modbus connection to UR10
        self.c = c if c else ModbusClient(host='172.20.1.50', port=502, auto_open=True)

        self.flag = False

        self.registers = [
                [[0], 400],
                [[0], 401],
                [[0], 402],
                [[0], 403],
                [[0], 404],
                [[0], 405],
                [[0], 450]
                ]

        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']

        self.kxml_handler = KXMLHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.kxml_handler, path=os.getcwd(), recursive=False)
        self.observer.start()

        self.kxml_data = []
        self.kxml_cols = ['Time(ms)', 'Nset(1/min)', 'Torque(Nm)', 'Current(V)', 'Angle(°)', 'Depth(mm)']

        # Set up the variables for the PLC signal monitoring
        self.counter = 1
        ext_dir = os.getcwd()+'/data'
        self.directory = os.path.expanduser(ext_dir)

        self.data = []


    #magic conversion function
    def unsigned(self, a):
        if a > 32767:
            a = a - 65535
        else:
            a = a
        return a


    def plc_run(self):
        while self.running:
            for reg in self.registers:
                try:
                    val = self.c.read_holding_registers(reg[1])[0]
                    if val is not None:
                        reg[0] = val
                except Exception:
                    pass
            
            if socketio:
                modbus_data = {}
                for i, reg in enumerate(self.registers):
                    val = self.unsigned(reg[0])
                    
                    if i < 3:
                        val /= 10.0
                    else:
                        val /= 1000.0
                    modbus_data[self.cols[i+1]] = val
                socketio.emit('modbus_data', modbus_data)
            
            time.sleep(0.1) # Frequency of monitoring


    def run(self):
        while self.running:
            reading = self.client.db_read(self.db_number, self.start_offset, 1)
            result = snap7.util.get_bool(reading, 0, self.bit_offset)

            if result and not self.flag:
                self.flag = True
                start_time = datetime.now()
                self.data = []
            
            if self.flag:
                current_time = datetime.now()
                elapsed_time = (current_time - start_time).total_seconds() * 1000
                line = []
                line.append(elapsed_time)
                for reg in self.registers:
                    line.append(reg[0][0])
                self.data.append(line)
                # print(line)
                
                # If the PLC signal is False or if the recording has reached its maximum duration, stop recording
                if not result:
                    self.flag = False
                    

    def kxml_ingest(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # 1. Extract X-Axis
        x_axis = root.find(".//X_Axis")
        if x_axis is not None:
            values = [float(v.text) for v in x_axis.findall("Values/float")]
            self.kxml_data.append(values)

        # 2. Extract all Y-Axes
        y_axes = root.findall(".//Y_AxesList/AxisData")
        for axis in y_axes:
            values = [float(v.text) for v in axis.findall("Values/float")]
            self.kxml_data.append(values)

    def save_data(self, classification):
        self.counter += 1
        df = pd.DataFrame(data=self.data, columns=self.cols)
        df = df.map(self.unsigned)
        df[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
        df[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000
 
        filename_t = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_robot")
        df.to_csv(filename_t+".csv", index=False)

        df_kxml = pd.DataFrame(data=self.kxml_data, columns=self.kxml_cols)
        filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_kxml")
        df_kxml.to_csv(filename_kxml+".csv", index=False)



# create flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Placeholder for the collector
w = None

# main flask page
@app.route('/')
def index():
    return "API is running"

@app.route('/data')
def get_data():
    if w:
        return {"data": w.data}
    return {"data": []}

@app.route('/kxml_data')
def get_kxml_data():
    if w:
        return {"kxml_data": w.kxml_data}
    return {"kxml_data": []}

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@app.route('/save/<classification>', methods=['POST'])
def save_data(classification):
    if w:
        w.save_data(classification)
        return {"status": "success"}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/set/counter/<int:counter>', methods=['POST'])
def set_counter(counter):
    if w:
        w.counter = counter
        return {"status": "success", "counter": w.counter}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/set/directory/<path:directory>', methods=['POST'])
def set_directory(directory):
    if w:
        w.directory = directory
        return {"status": "success", "directory": w.directory}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/get/param', methods=['GET'])
def get_param():
    if w:
        return {
            "counter": w.counter,
            "directory": w.directory,
        }
    return {"status": "error", "message": "Collector not initialized"}, 500


## Main funcion, only initiate the Flask app
def main(args=None):
    global w
    w = collector()
    Thread(target=w.run).start()
    Thread(target=w.plc_run).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

def fake_main(args=None):
    global w
    import fake_collector
    w = fake_collector.FakeCollector(socketio=socketio)
    Thread(target=w.run).start()
    Thread(target=w.plc_run).start()
    print("Running in FAKE mode with precollected data")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    # Change to main() to use real hardware
    fake_main()
