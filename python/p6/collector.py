import snap7
import time
import os
import pandas as pd
from datetime import datetime
from pyModbusTCP.client import ModbusClient
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import xml.etree.ElementTree as ET


class KXMLHandler(FileSystemEventHandler):
    def __init__(self, collector):
        self.collector = collector

    def on_created(self, event):
        if event.src_path.endswith('.KXML'):
            # Small delay to ensure the file is written
            time.sleep(0.5)
            self.collector.kxml_ingest(event.src_path)


class Collector():
    def __init__(self, client=None, c=None, socketio=None):
        self.running = True
        self.old_datasets = []
        self.collect = False
        self.socketio = socketio

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

        self.cols = ['Time (ms)', 'TCP_x (mm)', 'TCP_y (mm)', 'TCP_z (mm)', 
                     'TCP_rx (mm)', 'TCP_ry (mm)', 'TCP_rz (mm)', 'Robot_I (A)']

        self.directory = 'data/'
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)

        self.kxml_handler = KXMLHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.kxml_handler, path=self.directory, recursive=False)
        self.observer.start()

        self.kxml_data = []
        self.kxml_cols = ['Time (ms)', 'Nset (1/min)', 'Torque (Nm)', 'Current (V)', 'Angle (deg)', 'Depth (mm)']

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
            
            modbus_data = {}
            for i, reg in enumerate(self.registers):
                val = self.unsigned(reg[0])
                
                if i < 3:
                    val /= 10.0
                else:
                    val /= 1000.0
                modbus_data[self.cols[i+1]] = val
            self.socketio.emit('modbus_data', modbus_data)
            
            time.sleep(0.1) # Frequency of monitoring


    def run(self):
        while self.running:
            try:
                reading = self.client.db_read(self.db_number, self.start_offset, 1)
                result = snap7.util.get_bool(reading, 0, self.bit_offset)

                if result and not self.flag:
                    self.flag = True
                    self.socketio.emit('recording_status', {'status': 'started'})
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
                        self.socketio.emit('recording_status', {'status': 'stopped'})
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
            self.socketio.emit('runFinished', {'status': 'complete'})
            if self.collect:
                # Use last_finished_data to ensure we get the data from the run that just stopped
                self.old_datasets.append([list(self.kxml_data), self.last_finished_data])
                self.socketio.emit('collection_updated', {'count': len(self.old_datasets), 'collect': self.collect})
        except Exception as e:
            print(f"Error ingesting KXML {file_path}: {e}")

    def save_data(self, classification):
        self.counter += 1
        df = pd.DataFrame(data=self.data, columns=self.cols)
        df = df.map(self.unsigned)
        df[['TCP_x (mm)', 'TCP_y (mm)', 'TCP_z (mm)']] /= 10
        df[['TCP_rx (mm)', 'TCP_ry (mm)', 'TCP_rz (mm)', 'Robot_I (A)']] /= 1000

        filename_t = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_robot")
        df.to_csv(filename_t+".csv", index=False)

        try:
            # Always zip to transpose column-wise kxml_data to row-wise
            df_kxml = pd.DataFrame(data=list(zip(*self.kxml_data)), columns=self.kxml_cols[:len(self.kxml_data)])
        except Exception:
            df_kxml = pd.DataFrame(data=list(zip(*self.kxml_data)))

        filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_kxml")
        df_kxml.to_csv(filename_kxml+".csv", index=False)
    def save_all(self, classifications):
        for i, dataset in enumerate(self.old_datasets):
            kxml_data, modbus_data = dataset
            classification = classifications[i] if i < len(classifications) else "unknown"
            
            try:
                df_kxml = pd.DataFrame(data=list(zip(*kxml_data)), columns=self.kxml_cols[:len(kxml_data)])
            except Exception:
                df_kxml = pd.DataFrame(data=list(zip(*kxml_data)))
            filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_kxml")
            df_kxml.to_csv(filename_kxml+".csv", index=False)

            df_modbus = pd.DataFrame(data=modbus_data, columns=self.cols)
            df_modbus = df_modbus.map(self.unsigned)
            df_modbus[['TCP_x (mm)', 'TCP_y (mm)', 'TCP_z (mm)']] /= 10
            df_modbus[['TCP_rx (mm)', 'TCP_ry (mm)', 'TCP_rz (mm)', 'Robot_I (A)']] /= 1000
            filename_modbus = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_robot")
            df_modbus.to_csv(filename_modbus+".csv", index=False)
            self.counter += 1
        
        self.old_datasets = []
