import os
import pandas as pd
import time
import xml.etree.ElementTree as ET

class FakeCollector:
    def __init__(self, socketio=None):
        self.counter = 0
        self.directory = "/data"
        self.running = True
        self.socketio = socketio
        self.data = []
        self.kxml_data = []
        self.cols = ['Time(ms)', 'TCP_x(mm)', 'TCP_y(mm)', 'TCP_z(mm)', 
                     'TCP_rx(mm)', 'TCP_ry(mm)', 'TCP_rz(mm)', 'Robot_I(A)']
        
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.file_sets = self._discover_file_sets()
        self.current_set_index = 0

    def _discover_file_sets(self):
        """Discovers matching pairs of .csv and .KXML files."""
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

    def plc_run(self):
        """Simulates the data emission and collection cycle."""
        while self.running:
            if not self.file_sets:
                print("No matching file sets (CSV + KXML) found in data directory.")
                time.sleep(5)
                continue

            current_set = self.file_sets[self.current_set_index]
            csv_path = current_set['csv']
            kxml_path = current_set['kxml']

            # 1. Reset data for the new cycle
            print(f"Starting new cycle with set: {os.path.basename(csv_path)} and {os.path.basename(kxml_path)}")
            self.data = []
            self.kxml_data = []

            # 2. Replay the CSV
            print(f"Replaying {csv_path}")
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                print(f"Error reading CSV {csv_path}: {e}")
                self.current_set_index = (self.current_set_index + 1) % len(self.file_sets)
                continue

            for _, row in df.iterrows():
                if not self.running:
                    break
                
                # Emit modbus data via socketio
                modbus_data = {col: row[col] for col in self.cols[1:]}
                if self.socketio:
                    self.socketio.emit('modbus_data', modbus_data)
                
                # Record into self.data
                self.data.append(row.tolist())
                
                # Fixed rate simulation (50ms as in previous version)
                time.sleep(0.01) # Sped up slightly for better dev experience, but can be adjusted

            if not self.running:
                break

            # 3. Read the KXML
            print(f"Ingesting {kxml_path}")
            self.kxml_ingest(kxml_path)

            # 4. Wait 2 seconds
            print("Cycle finished. Waiting 2 seconds before next reset.")
            time.sleep(5)

            # Move to next set
            self.current_set_index = (self.current_set_index + 1) % len(self.file_sets)

    def run(self):
        """Interface compatibility sleep loop."""
        while self.running:
            time.sleep(1)

    def stop(self):
        self.running = False

    def kxml_ingest(self, file_path):
        """Mimics the KXML ingestion from the real collector."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Reset kxml_data before ingest as per 'reset and repeat'
            # (Though plc_run already does it, we keep it consistent)
            ingested_data = []

            # 1. Extract X-Axis
            x_axis = root.find(".//X_Axis")
            if x_axis is not None:
                values = [float(v.text) for v in x_axis.findall("Values/float")]
                ingested_data.append(values)

            # 2. Extract all Y-Axes
            y_axes = root.findall(".//Y_AxesList/AxisData")
            for axis in y_axes:
                values = [float(v.text) for v in axis.findall("Values/float")]
                ingested_data.append(values)
            
            self.kxml_data = ingested_data
            print(f"Successfully ingested {len(ingested_data)} axes from KXML.")
            
            # Emit event that kxml is ready if needed (optional, but good for UX)
            if self.socketio:
                self.socketio.emit('kxml_ready', {'file': os.path.basename(file_path)})

        except Exception as e:
            print(f"Error ingesting KXML {file_path}: {e}")
