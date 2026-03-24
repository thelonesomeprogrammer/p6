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
from flask import request
import numpy as np

def lttb_indices(data_x, data_y, threshold):
    """
    Calculates the indices of points to keep using LTTB.
    data_x: 1D array-like
    data_y: 1D array-like
    threshold: number of points to keep
    Returns: list of indices
    """
    n_points = len(data_x)
    if threshold >= n_points or threshold <= 2:
        return list(range(n_points))

    data_x = np.array(data_x)
    data_y = np.array(data_y)

    n_bins = threshold - 2
    bin_size = (n_points - 2) / n_bins
    
    indices = [0] # Always keep first point
    
    for i in range(n_bins):
        # Calculate range for current bin
        start = int(np.floor((i) * bin_size) + 1)
        end = int(np.floor((i + 1) * bin_size) + 1)
        
        # Calculate range for next bin to calculate average point
        next_start = int(np.floor((i + 1) * bin_size) + 1)
        next_end = int(np.floor((i + 2) * bin_size) + 1)
        
        if next_end > n_points:
            next_end = n_points
            
        avg_x_next = np.mean(data_x[next_start:next_end])
        avg_y_next = np.mean(data_y[next_start:next_end])
        
        a_x = data_x[indices[-1]]
        a_y = data_y[indices[-1]]
        
        # Optimize triangle area calculation
        # Area = 0.5 * |x1(y2-y3) + x2(y3-y1) + x3(y1-y2)|
        term1 = avg_y_next - a_y
        
        bin_x = data_x[start:end]
        bin_y = data_y[start:end]
        
        areas = 0.5 * np.abs(
            a_x * (bin_y - avg_y_next) + 
            bin_x * term1 + 
            avg_x_next * a_y - avg_x_next * bin_y
        )
        
        selected_index = start + np.argmax(areas)
        indices.append(selected_index)
        
    indices.append(n_points - 1) # Always keep last point
    return indices


class KXMLHandler(FileSystemEventHandler):
    def __init__(self, collector):
        self.collector = collector

    def on_created(self, event):
        if event.src_path.endswith('.kxml'):
            # Small delay to ensure the file is written
            time.sleep(0.5)
            self.collector.kxml_ingest(event.src_path)


class collector():
    def __init__(self, client=None, c=None):
        self.running = True
        self.old_datasets = []
        self.collect = False

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
                [0, 400],
                [0, 401],
                [0, 402],
                [0, 403],
                [0, 404],
                [0, 405],
                [0, 450]
                ]

        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']

        ext_dir = os.path.join(os.getcwd(), 'data')
        self.directory = os.path.expanduser(ext_dir)
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        self.kxml_handler = KXMLHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.kxml_handler, path=self.directory, recursive=False)
        self.observer.start()

        self.kxml_data = []
        self.kxml_cols = ['Time(ms)', 'Nset(1/min)', 'Torque(Nm)', 'Current(V)', 'Angle(°)', 'Depth(mm)']

        # Set up the variables for the PLC signal monitoring
        self.counter = 1
        self.data = []
        self.last_finished_data = []


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
            try:
                reading = self.client.db_read(self.db_number, self.start_offset, 1)
                result = snap7.util.get_bool(reading, 0, self.bit_offset)

                if result and not self.flag:
                    self.flag = True
                    socketio.emit('recording_status', {'status': 'started'})
                    start_time = datetime.now()
                    self.data = []
                
                if self.flag:
                    current_time = datetime.now()
                    elapsed_time = (current_time - start_time).total_seconds() * 1000
                    line = []
                    line.append(elapsed_time)
                    for reg in self.registers:
                        line.append(reg[0])
                    self.data.append(line)
                    
                    if not result:
                        self.flag = False
                        self.last_finished_data = list(self.data)
                        socketio.emit('recording_status', {'status': 'stopped'})
            except Exception as e:
                print(f"Error in run loop: {e}")
                time.sleep(1)
                    

    def kxml_ingest(self, file_path):
        try:
            self.kxml_data = []
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
            
            print(f"Ingested KXML: {file_path}")
            socketio.emit('runFinished', {'status': 'complete'})
            if self.collect:
                # Use last_finished_data to ensure we get the data from the run that just stopped
                self.old_datasets.append([list(self.kxml_data), self.last_finished_data])
        except Exception as e:
            print(f"Error ingesting KXML {file_path}: {e}")

    def save_data(self, classification):
        self.counter += 1
        df = pd.DataFrame(data=self.data, columns=self.cols)
        df = df.map(self.unsigned)
        df[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
        df[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000
 
        filename_t = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_robot")
        df.to_csv(filename_t+".csv", index=False)

        try:
            if len(self.kxml_data) == len(self.kxml_cols):
                df_kxml = pd.DataFrame(data=list(zip(*self.kxml_data)), columns=self.kxml_cols)
            else:
                df_kxml = pd.DataFrame(data=self.kxml_data, columns=self.kxml_cols)
        except Exception:
            df_kxml = pd.DataFrame(data=self.kxml_data)

        filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_kxml")
        df_kxml.to_csv(filename_kxml+".csv", index=False)

    def save_all(self, classifications):
        for i, dataset in enumerate(self.old_datasets):
            kxml_data, modbus_data = dataset
            classification = classifications[i] if i < len(classifications) else "unknown"
            
            df_kxml = pd.DataFrame(data=list(zip(*kxml_data)), columns=self.kxml_cols)
            filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_kxml")
            df_kxml.to_csv(filename_kxml+".csv", index=False)

            df_modbus = pd.DataFrame(data=modbus_data, columns=self.cols)
            df_modbus = df_modbus.map(self.unsigned)
            df_modbus[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
            df_modbus[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000
            filename_modbus = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_robot")
            df_modbus.to_csv(filename_modbus+".csv", index=False)
            self.counter += 1
        
        self.old_datasets = []



# create flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Placeholder for the collector
w = None

# main flask page
@app.route('/')
def index():
    return "API is running"

@app.route('/data')
def get_data():
    if not w or not w.data:
        return {"data": []}
    
    threshold = request.args.get('points', default=500, type=int)
    
    # 1. Transform raw registers to scaled/unsigned data
    df = pd.DataFrame(data=w.data, columns=w.cols)
    df = df.map(w.unsigned)
    df[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
    df[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000
    
    # 2. Downsample if needed
    if len(df) > threshold:
        # Using first Y axis ('TCP_x(mm)') as reference for LTTB
        indices = lttb_indices(df[w.cols[0]].values, df[w.cols[1]].values, threshold)
        df = df.iloc[indices].copy()
        
    df['Time(ms)'] = df['Time(ms)'].round().astype(int)
    return {"data": df.to_dict(orient='records')}

@app.route('/kxml_data')
def get_kxml_data():
    if not w or not w.kxml_data:
        return {"kxml_data": []}
    
    threshold = request.args.get('points', default=500, type=int)
    
    # w.kxml_data is a list of columns
    num_rows = len(w.kxml_data[0])
    num_cols = len(w.kxml_data)
    
    # 1. Transform into a DataFrame for easier handling
    col_names = w.kxml_cols[:num_cols] if len(w.kxml_cols) >= num_cols else [f"Col{i}" for i in range(num_cols)]
    
    try:
        # Transpose column-wise to row-wise
        row_data = list(zip(*w.kxml_data))
        df = pd.DataFrame(data=row_data, columns=col_names)
    except Exception as e:
        print(f"Error transposing kxml_data: {e}")
        return {"kxml_data": []}
    
    # 2. Downsample if needed
    if len(df) > threshold:
        # Using first Y axis (index 1) as reference for LTTB
        indices = lttb_indices(df.iloc[:, 0].values, df.iloc[:, 1].values, threshold)
        df = df.iloc[indices].copy()
    
    if 'Time(ms)' in df.columns:
        df['Time(ms)'] = df['Time(ms)'].round().astype(int)
    
    return {"kxml_data": df.to_dict(orient='records')}

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@app.route('/start_collection', methods=['POST'])
def start_collection():
    if w:
        w.collect = True
        return {"status": "success", "message": "Data collection started"}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/stop_collection', methods=['POST'])
def stop_collection():
    if w:
        w.collect = False
        return {"status": "success", "message": "Data collection stopped"}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/get_collect')
def get_collection():
    if w:
        return {"collect": w.collect}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/get_collection_count')
def get_collection_count():
    if w:
        return {"count": len(w.old_datasets)}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/save_all', methods=['POST'])
def save_all():
    if w:
        classifications = request.json.get('classifications', [])
        w.save_all(classifications)
        return {"status": "success"}
    return {"status": "error", "message": "Collector not initialized"}, 500

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
