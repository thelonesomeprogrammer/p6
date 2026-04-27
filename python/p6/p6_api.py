import os
import threading
from .main import app as real_app, socketio as real_socketio, main as main_real, fake_main as main_fake
from .socket_faker import app as faker_app, socketio as faker_socketio, streamer as faker_streamer
from . import train_ml
from . import train_lstm
from . import train_regression
from . import utils

class Options:
    # training paths
    DATA_DIR_ML = "prev-data/Dataset/Intrinsic data"
    N_DATA_DIR = "prev-data/Dataset/Intrinsic data/N"
    OT_DATA_DIR = "prev-data/Dataset/Intrinsic data/OT"
    OT_LABELS_PATH = "prev-data/ot_labels.csv"
    
    # model save paths
    ML_MODEL_PATH = "predictors_ml.joblib"
    REG_MODEL_PATH = "regressors_ml.joblib"
    LSTM_MODEL_PATH = "lstm_regressor.pth"
    LSTM_SCALER_PATH = "lstm_scaler.joblib"

    # feature selection
    INPUT_FEATURES = utils.INPUT_FEATURES
    TARGET_COLUMN = utils.TARGET_COLUMN

def start_real_server(port=5000, host='0.0.0.0'):
    """Starts the real fetch-based server with hardware collector."""
    thread = threading.Thread(target=main_real)
    thread.daemon = True
    thread.start()
    return thread

def start_fake_server(port=5000, host='0.0.0.0'):
    """Starts the fake fetch-based server with precollected data."""
    thread = threading.Thread(target=main_fake)
    thread.daemon = True
    thread.start()
    return thread

def start_socket_faker(port=5001, host='0.0.0.0'):
    """Starts the fake socket server that streams data."""
    def run_faker():
        faker_streamer.start()
        faker_socketio.run(faker_app, host=host, port=port, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=run_faker)
    thread.daemon = True
    thread.start()
    return thread

def train_classification():
    """Exposes the ML classification training."""
    train_ml.DATA_DIR = Options.DATA_DIR_ML
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    train_ml.main()

def train_lstm_remaining():
    """Exposes the LSTM regression training."""
    train_lstm.N_DATA_DIR = Options.N_DATA_DIR
    train_lstm.OT_DATA_DIR = Options.OT_DATA_DIR
    train_lstm.OT_LABELS_PATH = Options.OT_LABELS_PATH
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    utils.TARGET_COLUMN = Options.TARGET_COLUMN
    train_lstm.main()

def train_regression_remaining():
    """Exposes the ML regression training."""
    train_regression.N_DATA_DIR = Options.N_DATA_DIR
    train_regression.OT_DATA_DIR = Options.OT_DATA_DIR
    train_regression.OT_LABELS_PATH = Options.OT_LABELS_PATH
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    utils.TARGET_COLUMN = Options.TARGET_COLUMN
    train_regression.main()
