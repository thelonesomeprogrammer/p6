import os
import pandas as pd
import time
import xml.etree.ElementTree as ET
from datetime import datetime

class FakeCollector:
    def __init__(self, socketio=None):
        self.running = True
        self.socketio = socketio
        
        self.today = datetime.today().strftime('%d%m%Y')
        self.flag = False
        
        # registers: [current_val, address] - matching main.py's collector
        self.registers = [
            [0, 400], [0, 401], [0, 402], [0, 403], 
            [0, 404], [0, 405], [0, 450]
        ]
        
        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']
        
        self.kxml_data = []
        self.kxml_cols = ['Time(ms)', 'Nset(1/min)', 'Torque(Nm)', 'Current(V)', 'Angle(°)', 'Depth(mm)']
        
        self.counter = 1
        self.directory = 'data/'
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)
        
        self.data = []
        self.old_datasets = []
        self.collect = False
        
        # Faker specific: discover available data sets for simulation
        self.data_dir = self.directory
        self.file_sets = self._discover_file_sets()
        self.current_set_index = 0

    def _discover_file_sets(self):
        """Discovers matching pairs of .csv and .KXML files."""
        if not os.path.exists(self.data_dir):
            print(f"FakeCollector: Data directory {self.data_dir} not found.")
            return []
            
        csv_files = [f for f in os.listdir(self.data_dir) if f.startswith('data_') and f.endswith('.csv')]
        sets = []
        for csv_f in csv_files:
            try:
                # Extract number from data_N.csv
                num_str = csv_f.replace('data_', '').replace('.csv', '')
                num = int(num_str)
                # Look for matching _00N.KXML
                kxml_f = f"_{num:03d}.KXML"
                if os.path.exists(os.path.join(self.data_dir, kxml_f)):
                    sets.append({
                        'csv': os.path.join(self.data_dir, csv_f),
                        'kxml': os.path.join(self.data_dir, kxml_f)
                    })
            except ValueError:
                continue
        return sorted(sets, key=lambda x: x['csv'])

    def unsigned(self, a):
        """Magic conversion function matching main.py."""
        if a > 32767:
            a = a - 65535
        else:
            a = a
        return a

    def plc_run(self):
        """Simulates Modbus data emission and cycle management."""
        while self.running:
            if not self.file_sets:
                print("FakeCollector: No matching file sets (CSV + KXML) found.")
                time.sleep(5)
                continue

            current_set = self.file_sets[self.current_set_index]
            csv_path = current_set['csv']
            kxml_path = current_set['kxml']

            print(f"FakeCollector: Starting cycle with {os.path.basename(csv_path)}")
            
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                print(f"FakeCollector: Error reading {csv_path}: {e}")
                self.current_set_index = (self.current_set_index + 1) % len(self.file_sets)
                continue

            # Reset data for the new recording cycle
            self.data = []
            self.kxml_data = []
            self.flag = True
            
            if self.socketio:
                self.socketio.emit('recording_status', {'status': 'started'})

            start_time = datetime.now()

            for _, row in df.iterrows():
                if not self.running:
                    break
                
                # Update registers with "unscaled" values so save_data works correctly
                # main.py scales: /10 for x,y,z and /1000 for rx,ry,rz,I
                self.registers[0][0] = int(row['TCP_x(mm)'] * 10)
                self.registers[1][0] = int(row['TCP_y(mm)'] * 10)
                self.registers[2][0] = int(row['TCP_z(mm)'] * 10)
                self.registers[3][0] = int(row['TCP_rx(mm)'] * 1000)
                self.registers[4][0] = int(row['TCP_ry(mm)'] * 1000)
                self.registers[5][0] = int(row['TCP_rz(mm)'] * 1000)
                self.registers[6][0] = int(row['Robot_I(A)'] * 1000)

                # Emit scaled modbus data via socketio (matching main.py's emission)
                modbus_data = {col: row[col] for col in self.cols[1:]}
                if self.socketio:
                    self.socketio.emit('modbus_data', modbus_data)
                
                # Record into self.data (matching main.py's run loop behavior)
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                line = [elapsed_ms] + [reg[0] for reg in self.registers]
                self.data.append(line)
                
                # Simulation speed
                time.sleep(0.01)

            self.flag = False
            if self.socketio:
                self.socketio.emit('recording_status', {'status': 'stopped'})

            # Ingest KXML after recording stops
            self.kxml_ingest(kxml_path)

            print("FakeCollector: Cycle finished. Waiting 5 seconds.")
            time.sleep(5)
            self.current_set_index = (self.current_set_index + 1) % len(self.file_sets)

    def run(self):
        """Interface compatibility loop."""
        while self.running:
            time.sleep(1)

    def kxml_ingest(self, file_path):
        """Mimics main.py's KXML ingestion."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            ingested_axes = []
            # 1. Extract X-Axis
            x_axis = root.find(".//X_Axis")
            if x_axis is not None:
                values = [float(v.text) for v in x_axis.findall("Values/float")]
                ingested_axes.append(values)

            # 2. Extract all Y-Axes
            y_axes = root.findall(".//Y_AxesList/AxisData")
            for axis in y_axes:
                values = [float(v.text) for v in axis.findall("Values/float")]
                ingested_axes.append(values)
            
            self.kxml_data = ingested_axes
            print(f"FakeCollector: Ingested {len(ingested_axes)} axes from KXML.")
            if self.collect:
                # Need to copy data to avoid reference issues
                self.old_datasets.append([ingested_axes, list(self.data)])
                if self.socketio:
                    self.socketio.emit('collection_updated', {'count': len(self.old_datasets), 'collect': self.collect})
            if self.socketio:
                self.socketio.emit('kxml_ready')
        except Exception as e:
            print(f"FakeCollector: Error ingesting KXML {file_path}: {e}")

        self.socketio.emit('runFinished', {'status': 'complete'})

    def save_data(self, classification):
        """Mimics main.py's save_data exactly, including the likely column bug."""
        self.counter += 1
        df = pd.DataFrame(data=self.data, columns=self.cols)
        df = df.map(self.unsigned)
        df[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
        df[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000
 
        filename_t = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_robot")
        df.to_csv(filename_t+".csv", index=False)

        # We use zip(*data) to fix the likely bug where axes are appended as columns but saved as rows
        try:
            if len(self.kxml_data) == len(self.kxml_cols):
                df_kxml = pd.DataFrame(data=list(zip(*self.kxml_data)), columns=self.kxml_cols)
            else:
                df_kxml = pd.DataFrame(data=self.kxml_data, columns=self.kxml_cols)
        except Exception:
            df_kxml = pd.DataFrame(data=self.kxml_data)

        filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter}_{classification}_kxml")
        df_kxml.to_csv(filename_kxml+".csv", index=False)
        print(f"FakeCollector: Data saved for {classification}")

    def save_all(self, classifications):
        """Saves all datasets in old_datasets and clears the list."""
        for i, dataset in enumerate(self.old_datasets):
            kxml_data, modbus_data = dataset
            # Use current classification or default to 'unknown'
            classification = classifications[i] if i < len(classifications) else "unknown"
            
            df_kxml = pd.DataFrame(data=list(zip(*kxml_data)), columns=self.kxml_cols)
            filename_kxml = os.path.join(self.directory, f"data_{self.today}_{self.counter + i}_{classification}_kxml")
            df_kxml.to_csv(filename_kxml+".csv", index=False)

            df_modbus = pd.DataFrame(data=modbus_data, columns=self.cols)
            df_modbus = df_modbus.map(self.unsigned)
            df_modbus[['TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)']] /= 10
            df_modbus[['TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']] /= 1000
            filename_modbus = os.path.join(self.directory, f"data_{self.today}_{self.counter + i}_{classification}_robot")
            df_modbus.to_csv(filename_modbus+".csv", index=False)
            
        self.counter += len(self.old_datasets)
        self.old_datasets = []
        print(f"FakeCollector: Saved {len(classifications)} datasets.")
        if self.socketio:
            self.socketio.emit('collection_updated', {'count': len(self.old_datasets), 'collect': self.collect})
            self.socketio.emit('params_updated', {'counter': self.counter, 'directory': self.directory})

    def stop(self):
        self.running = False
