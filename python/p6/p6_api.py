import threading
from . import utils

class Options:
    # training paths
    DATA_DIR_ML = "prev-data/Dataset/Intrinsic data"
    N_DATA_DIR = "prev-data/Dataset/Intrinsic data/N"
    OT_DATA_DIR = "prev-data/Dataset/Intrinsic data/OT"
    OT_DATA_DIR_SLIDE = "prev-data/OT_truncated_intrinsic_833Hz/"
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
    from .main import main as main_real
    thread = threading.Thread(target=main_real)
    thread.daemon = True
    thread.start()
    return thread

def start_fake_server(port=5000, host='0.0.0.0'):
    """Starts the fake fetch-based server with precollected data."""
    from .main import fake_main as main_fake
    thread = threading.Thread(target=main_fake)
    thread.daemon = True
    thread.start()
    return thread

def start_socket_faker(port=5001, host='0.0.0.0'):
    """Starts the fake socket server that streams data."""
    from .socket_faker import app as faker_app, socketio as faker_socketio, streamer as faker_streamer
    def run_faker():
        faker_streamer.start()
        faker_socketio.run(faker_app, host=host, port=port, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=run_faker)
    thread.daemon = True
    thread.start()
    return thread

def train_classification():
    """Exposes the ML classification training."""
    from . import train_ml
    train_ml.DATA_DIR = Options.DATA_DIR_ML
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    train_ml.main()

def train_lstm_remaining():
    """Exposes the LSTM regression training."""
    from . import train_lstm
    train_lstm.N_DATA_DIR = Options.N_DATA_DIR
    train_lstm.OT_DATA_DIR = Options.OT_DATA_DIR
    train_lstm.OT_LABELS_PATH = Options.OT_LABELS_PATH
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    utils.TARGET_COLUMN = Options.TARGET_COLUMN
    train_lstm.main()

def train_regression_remaining():
    """Exposes the ML regression training."""
    from . import train_regression
    train_regression.N_DATA_DIR = Options.N_DATA_DIR
    train_regression.OT_DATA_DIR = Options.OT_DATA_DIR
    train_regression.OT_LABELS_PATH = Options.OT_LABELS_PATH
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    utils.TARGET_COLUMN = Options.TARGET_COLUMN
    train_regression.main()

def train_regression_sliding():
    """Exposes the sliding window ML regression training."""
    from . import train_reg_slide
    train_reg_slide.OT_DATA_DIR = Options.OT_DATA_DIR_SLIDE
    train_reg_slide.OT_LABELS_PATH = Options.OT_LABELS_PATH
    utils.INPUT_FEATURES = Options.INPUT_FEATURES
    utils.TARGET_COLUMN = Options.TARGET_COLUMN
    train_reg_slide.main()
