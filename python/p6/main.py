from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from threading import Thread
import pandas as pd
from flask import request
from ._p6 import lttb_indices
from .collector import Collector
from .predictor import MLPredictor, RegressionPredictor, LSTMPredictor, SlidingPredictor
import os

# create flask app
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize predictors
predictor_rf = None
predictor_gb = None
predictor_reg_rf = None
predictor_lstm = None
predictor_slide = None

try:
    predictor_rf = MLPredictor(model_type="rf")
    predictor_gb = MLPredictor(model_type="gb")
    predictor_reg_rf = RegressionPredictor(model_type="rf_regressor")
    predictor_lstm = LSTMPredictor()
    predictor_slide = SlidingPredictor(model_type="rf")
except Exception as e:
    print(f"Warning: ML Predictors not loaded: {e}")

# Placeholder for the collector
w = None

@app.route('/version')
def version():
    if not w:
        return {"version": "collector-not-initialized"}
    if type(w).__name__ == "FakeCollector":
        return {"version": "collector-fake"}
    if type(w).__name__ == "Collector":
        return {"version": "collector-real"}
    return {"version": "collector-unknown"}

@app.route('/predict')
def predict_kxml():
    if not w or not w.kxml_data:
        return {"error": "No KXML data available"}, 400
    
    model_type = request.args.get('model', default='rf', type=str)
    predictor = predictor_gb if model_type == 'gb' else predictor_rf
    
    if not predictor:
        return {"error": "Predictor not loaded"}, 500

    try:
        # Transpose column-wise to row-wise
        row_data = list(zip(*w.kxml_data))
        num_cols = len(w.kxml_data)
        col_names = w.kxml_cols[:num_cols] if len(w.kxml_cols) >= num_cols else [f"Col{i}" for i in range(num_cols)]
        df = pd.DataFrame(data=row_data, columns=col_names)
        
        predictor.reset()
        result = predictor.predict(df)
        if result:
            return result
        else:
            return {"error": "Insufficient data for prediction"}, 400
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}, 500

@app.route('/predict_remaining')
def predict_remaining():
    if not w or not w.kxml_data:
        return {"error": "No KXML data available"}, 400
    
    model_type = request.args.get('model', default='rf', type=str)
    if model_type == 'lstm' and predictor_lstm:
        predictor = predictor_lstm
    elif model_type == 'sliding' and predictor_slide:
        predictor = predictor_slide
    else:
        predictor = predictor_reg_rf

    if not predictor:
        return {"error": "Regression Predictor not loaded"}, 500

    try:
        # Transpose column-wise to row-wise
        row_data = list(zip(*w.kxml_data))
        num_cols = len(w.kxml_data)
        col_names = w.kxml_cols[:num_cols] if len(w.kxml_cols) >= num_cols else [f"Col{i}" for i in range(num_cols)]
        df = pd.DataFrame(data=row_data, columns=col_names)
        
        predictor.reset()
        result = predictor.predict(df)
        if result:
            return result
        else:
            return {"error": "Insufficient data for prediction"}, 400
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}, 500

@app.route('/predict_all')
def predict_all():
    if not w or not w.kxml_data:
        return {"error": "No KXML data available"}, 400
    
    model_type = request.args.get('model', default='rf', type=str)
    predictor = predictor_gb if model_type == 'gb' else predictor_rf
    
    if not predictor:
        return {"error": "Predictor not loaded"}, 500

    try:
        # Transpose column-wise to row-wise
        row_data = list(zip(*w.kxml_data))
        num_cols = len(w.kxml_data)
        col_names = w.kxml_cols[:num_cols] if len(w.kxml_cols) >= num_cols else [f"Col{i}" for i in range(num_cols)]
        df = pd.DataFrame(data=row_data, columns=col_names)
        
        n_rows = len(df)
        results = []
        
        # Reset all predictors for a clean incremental run
        predictor.reset()
        if predictor_reg_rf: predictor_reg_rf.reset()
        if predictor_lstm: predictor_lstm.reset()
        if predictor_slide: predictor_slide.reset()

        # 4 window stops: 25%, 50%, 75%, 100%
        for i in range(1, 5):
            percent = i / 4
            idx = max(2, int(n_rows * percent))
            window = df.iloc[:idx]
            
            res = predictor.predict(window)
            if res:
                res["window_percent"] = int(percent * 100)
                
                # Add regression if available
                # Use LSTM if requested, otherwise fallback to RF
                if model_type == 'lstm' and predictor_lstm:
                    reg_res = predictor_lstm.predict(window)
                elif model_type == 'sliding' and predictor_slide:
                    reg_res = predictor_slide.predict(window)
                elif predictor_reg_rf:
                    reg_res = predictor_reg_rf.predict(window)
                else:
                    reg_res = None

                if reg_res:
                    res.update(reg_res)
                        
                results.append(res)
        
        return {"predictions": results}
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}, 500

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
        socketio.emit('collection_updated', {'count': len(w.old_datasets), 'collect': w.collect})
        return {"status": "success", "message": "Data collection started"}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/stop_collection', methods=['POST'])
def stop_collection():
    if w:
        w.collect = False
        socketio.emit('collection_updated', {'count': len(w.old_datasets), 'collect': w.collect})
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
        socketio.emit('collection_updated', {'count': len(w.old_datasets), 'collect': w.collect})
        return {"status": "success"}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/save/<classification>', methods=['POST'])
def save_data(classification):
    if w:
        w.save_data(classification)
        socketio.emit('params_updated', {'counter': w.counter, 'directory': w.directory})
        return {"status": "success"}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/set/counter/<int:counter>', methods=['POST'])
def set_counter(counter):
    if w:
        w.counter = counter
        socketio.emit('params_updated', {'counter': w.counter, 'directory': w.directory})
        return {"status": "success", "counter": w.counter}
    return {"status": "error", "message": "Collector not initialized"}, 500

@app.route('/set/directory/<path:directory>', methods=['POST'])
def set_directory(directory):
    if w:
        w.directory = directory
        socketio.emit('params_updated', {'counter': w.counter, 'directory': w.directory})
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
    w = Collector(socketio=socketio)
    Thread(target=w.run).start()
    Thread(target=w.plc_run).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

def fake_main(args=None):
    global w
    from . import fake_collector
    w = fake_collector.FakeCollector(socketio=socketio)
    Thread(target=w.run).start()
    Thread(target=w.plc_run).start()
    print("Running in FAKE mode with precollected data")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    # Change to main() to use real hardware
    fake_main()
