import os
import random
import time
import threading
import pandas as pd
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from predictor import MLPredictor, RegressionPredictor, LSTMPredictor

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration
DATA_ROOT = "prev-data/Dataset"
INTRINSIC_DIR = os.path.join(DATA_ROOT, "Intrinsic data")
TASK_DIR = os.path.join(DATA_ROOT, "Task data")
ML_MODEL_PATH = "predictors_ml.joblib"
REG_MODEL_PATH = "regressors_ml.joblib"
LSTM_MODEL_PATH = "p6/lstm_regressor.pth"
LSTM_SCALER_PATH = "p6/lstm_scaler.joblib"

class Streamer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = False
        self.classifier = None
        self.regressor = None
        self.current_classifier_type = "rf"
        self.current_regressor_type = "rf_regressor"
        self.load_models()

    def load_models(self):
        try:
            self.classifier = MLPredictor(model_type=self.current_classifier_type, model_path=ML_MODEL_PATH)
            print(f"Loaded classifier: {self.current_classifier_type}")
        except Exception as e:
            print(f"Error loading classifier: {e}")
        
        try:
            if self.current_regressor_type == "lstm":
                self.regressor = LSTMPredictor(model_path=LSTM_MODEL_PATH, scaler_path=LSTM_SCALER_PATH)
            else:
                self.regressor = RegressionPredictor(model_type=self.current_regressor_type, model_path=REG_MODEL_PATH)
            print(f"Loaded regressor: {self.current_regressor_type}")
        except Exception as e:
            print(f"Error loading regressor: {e}")

    def set_classifier(self, model_type):
        self.current_classifier_type = model_type
        self.load_models()
        if self.classifier:
            self.classifier.reset()

    def set_regressor(self, model_type):
        self.current_regressor_type = model_type
        self.load_models()
        if self.regressor:
            self.regressor.reset()

    def get_random_pair(self):
        # Pick a random category (N, NS, OT, P, UT)
        categories = [d for d in os.listdir(INTRINSIC_DIR) if os.path.isdir(os.path.join(INTRINSIC_DIR, d))]
        categories.remove('P')
        cat = random.choice(categories)
        
        intrinsic_cat_dir = os.path.join(INTRINSIC_DIR, cat)
        files = [f for f in os.listdir(intrinsic_cat_dir) if f.endswith('.csv')]
        if not files:
            return None, None
        
        intrinsic_file = random.choice(files)
        # Corresponding task file has 't' instead of 'i'
        task_file = intrinsic_file.replace('i', 't', 1)
        task_path = os.path.join(TASK_DIR, cat, task_file)
        
        if not os.path.exists(task_path):
            return os.path.join(intrinsic_cat_dir, intrinsic_file), None
            
        return os.path.join(intrinsic_cat_dir, intrinsic_file), task_path

    def run(self):
        self.running = True
        while self.running:
            intrinsic_path, task_path = self.get_random_pair()
            if not intrinsic_path:
                time.sleep(1)
                continue
                
            print(f"Streaming: {intrinsic_path} and {task_path}")
            
            try:
                df_kxml = pd.read_csv(intrinsic_path)
                df_task = pd.read_csv(task_path) if task_path else None
                
                # Normalize columns to match frontend expectations (no spaces, specific units)
                kxml_map = {
                    "Time (ms)": "Time(ms)",
                    "Nset (1/min)": "Nset(1/min)",
                    "Torque (Nm)": "Torque(Nm)",
                    "Current (V)": "Current(V)",
                    "Angle (deg)": "Angle(°)",
                    "Depth (mm)": "Depth(mm)"
                }
                df_kxml = df_kxml.rename(columns=kxml_map)
                
                if df_task is not None:
                    task_map = {
                        "Time (ms)": "Time(ms)",
                        "TCP_x (mm)": "TCP_x(mm)",
                        "TCP_y (mm)": "TCP_y(mm)",
                        "TCP_z (mm)": "TCP_z(mm)",
                        "TCP_rx (rad)": "TCP_rx(mm)", # Frontend expects (mm) tag
                        "TCP_ry (rad)": "TCP_ry(mm)",
                        "TCP_rz (rad)": "TCP_rz(mm)",
                        "Robot_I (A)": "Robot_I(A)"
                    }
                    df_task = df_task.rename(columns=task_map)
            except Exception as e:
                print(f"Error reading CSVs: {e}")
                continue

            if self.classifier: 
                self.classifier.reset()
            if self.regressor: 
                self.regressor.reset()

            socketio.emit('recording_status', {'status': 'started'})
            socketio.emit('new_screw')
            start_time = time.time()
            last_pred_time = 0
            
            kxml_sum = {}
            modbus_sum = {}
            sample_count = 0
            
            # Stream kxml data line by line
            for i, row in df_kxml.iterrows():
                if not self.running:
                    break
                
                # Accumulate kxml data
                row_dict = row.to_dict()
                if not kxml_sum:
                    kxml_sum = {k: 0.0 for k in row_dict.keys()}
                for k, v in row_dict.items():
                    kxml_sum[k] += v
                
                # Accumulate robot data if available
                if df_task is not None and i < len(df_task):
                    task_row = df_task.iloc[i].to_dict()
                    if not modbus_sum:
                        modbus_sum = {k: 0.0 for k in task_row.keys()}
                    for k, v in task_row.items():
                        modbus_sum[k] += v
                
                sample_count += 1

                # Emit mean every 100 samples
                if sample_count >= 100:
                    kxml_mean = {k: v / sample_count for k, v in kxml_sum.items()}
                    socketio.emit('kxml_data', kxml_mean)
                    kxml_sum = {k: 0.0 for k in kxml_sum.keys()}
                    
                    if modbus_sum:
                        modbus_mean = {k: v / sample_count for k, v in modbus_sum.items()}
                        socketio.emit('modbus_data', modbus_mean)
                        modbus_sum = {k: 0.0 for k in modbus_sum.keys()}
                    
                    sample_count = 0

                # Predictions every 100ms
                current_elapsed = (time.time() - start_time) * 1000
                if current_elapsed - last_pred_time >= 500:
                    window = df_kxml.iloc[:i+1]
                    
                    predictions = {}
                    if self.classifier:
                        pred_class = self.classifier.predict(window)
                        if pred_class:
                            predictions['classification'] = pred_class
                            
                    if self.regressor:
                        pred_reg = self.regressor.predict(window)
                        if pred_reg:
                            predictions['regression'] = pred_reg
                    
                    if predictions:
                        socketio.emit('prediction', predictions)
                    
                    last_pred_time = current_elapsed

                # Sleep to maintain 1ms per line
                # Precise 1ms sleep is hard in Python, but we try
                elapsed = (time.time() - start_time)
                expected_time = (i + 1) * 0.01
                sleep_time = expected_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            socketio.emit('recording_status', {'status': 'stopped'})
            print("Cycle finished, waiting 2 seconds...")
            socketio.emit('cycle_finished')
            time.sleep(5)

streamer = Streamer()

@app.route('/set_classifier', methods=['POST'])
def set_classifier():
    data = request.json
    model_type = data.get('model_type')
    if model_type:
        streamer.set_classifier(model_type)
        return jsonify({"status": "success", "current_classifier": model_type})
    return jsonify({"status": "error", "message": "No model_type provided"}), 400

@app.route('/set_regressor', methods=['POST'])
def set_regressor():
    data = request.json
    model_type = data.get('model_type')
    if model_type:
        streamer.set_regressor(model_type)
        return jsonify({"status": "success", "current_regressor": model_type})
    return jsonify({"status": "error", "message": "No model_type provided"}), 400

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "classifier": streamer.current_classifier_type,
        "regressor": streamer.current_regressor_type,
        "running": streamer.running
    })

@app.route('/version', methods=['GET'])
def get_version():
    return {"version": "socket-faker"}

if __name__ == '__main__':
    streamer.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
