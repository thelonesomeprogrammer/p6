import os
import sys
import time
import pandas as pd
import numpy as np
import joblib
import torch
import torch.nn as nn
import pyarrow as pa
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure we can import from the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# If we are in the 'p6' package directory, add the parent so 'from p6 import ...' works
if os.path.basename(script_dir) == 'p6':
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

# Import models/utils
try:
    # Try local imports first to avoid shadowing by outdated installed packages
    import utils
    try:
        from extractor import FeatureExtractor
    except ImportError:
        from extractor import ExpandingFeatureExtractor as FeatureExtractor
except ImportError:
    try:
        # Fallback to package imports
        from p6 import utils
        try:
            from p6.extractor import FeatureExtractor
        except ImportError:
            from p6.extractor import ExpandingFeatureExtractor as FeatureExtractor
    except ImportError as e:
        print(f"Error: Could not import utils or extractor: {e}")
        print("Ensure p6 is installed or you are in the p6/python/p6 directory.")
        sys.exit(1)

try:
    from p6._p6 import RFPredictor, canonicalize_feature_name
except ImportError:
    try:
        from _p6 import RFPredictor, canonicalize_feature_name
    except ImportError:
        RFPredictor = None
        canonicalize_feature_name = None
        print("Warning: RFPredictor (Rust) not available.")

# ==========================================
# CNN-LSTM Architecture Definition
# ==========================================
class CNN_LSTM(nn.Module):
    def __init__(self, seq_len=200):
        super(CNN_LSTM, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=1, out_channels=64, kernel_size=5, padding=2)
        self.pool1 = nn.MaxPool1d(kernel_size=2)
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=64, kernel_size=3, padding=1)
        self.pool2 = nn.MaxPool1d(kernel_size=2)
        
        self.lstm = nn.LSTM(input_size=64, hidden_size=32, batch_first=True)
        
        self.fc1 = nn.Linear(32, 16)
        self.fc2 = nn.Linear(16, 1)

    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = self.pool1(x)
        x = torch.relu(self.conv2(x))
        x = self.pool2(x)
        
        x = x.transpose(1, 2)
        out, (hn, cn) = self.lstm(x)
        x = out[:, -1,:]
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

# Constants
USB_DIR = "usb"
OT_DATA_DIR = "prev-data/OT_truncated_intrinsic_833Hz"
OT_LABELS_PATH = "prev-data/ot_labels.csv"

# Top features

TOP_FEATURES_TSFEL = [
"torque_Spectral distance",
"torque_Slope",
"torque_Spectrogram mean coefficient_322.58Hz",
"torque_Human range energy",
"torque_Kurtosis",
"torque_Centroid",
"torque_Absolute energy",
"torque_Spectral decrease",
"torque_Mean diff",
"torque_Average power",
"torque_Wavelet absolute mean_104.17Hz",
"torque_Signal distance",
"torque_Variance",
"torque_Wavelet absolute mean_69.44Hz",
"torque_Wavelet variance_104.17Hz",
"torque_Spectrogram mean coefficient_268.82Hz",
"torque_Wavelet variance_69.44Hz",
]

OLD_TOP_FEATURES_TSFEL = [
    "torque_Max", "torque_Spectrogram mean coefficient_201.53Hz", "torque_Skewness",
    "torque_Spectrogram mean coefficient_40.31Hz", "torque_Min", "torque_Peak to peak distance",
    "torque_Mean diff", "torque_Spectrogram mean coefficient_53.74Hz", "torque_Kurtosis",
    "torque_Spectral decrease", "torque_Variance", "torque_Wavelet variance_208.25Hz",
    "torque_Spectrogram mean coefficient_67.18Hz", "torque_Spectral centroid",
    "torque_Wavelet variance_104.13Hz", "torque_Spectrogram mean coefficient_80.61Hz",
]

TOP_FEATURES_TSFRESH = [
"value__time_reversal_asymmetry_statistic__lag_2",
"value__benford_correlation",
"value__minimum",
"value__max_langevin_fixed_point__m_3__r_30",
"value__linear_trend__attr_\"rvalue\"",
"value__mean_n_absolute_max__number_of_maxima_7",
"value__time_reversal_asymmetry_statistic__lag_3",
"value__c3__lag_1",
"value__index_mass_quantile__q_0.3",
"value__time_reversal_asymmetry_statistic__lag_1",
"value__quantile__q_0.9",
"value__c3__lag_2",
"value__index_mass_quantile__q_0.4",
"value__sum_of_reoccurring_data_points",
"value__variance",
"value__agg_linear_trend__attr_\"slope\"__chunk_len_5__f_agg_\"mean\"",
"value__c3__lag_3",
"value__agg_linear_trend__attr_\"slope\"__chunk_len_10__f_agg_\"mean\"",
"value__sum_of_reoccurring_values",
"value__index_mass_quantile__q_0.2",
]

TOP_FEATURES_TSFRESH_XGB = [
    "value__maximum", "value__partial_autocorrelation__lag_2", "value__fft_coefficient__attr_\"real\"__coeff_8",
    "value__agg_linear_trend__attr_\"intercept\"__chunk_len_50__f_agg_\"var\"", "value__last_location_of_maximum",
    "value__fft_coefficient__attr_\"real\"__coeff_1", "value__agg_linear_trend__attr_\"stderr\"__chunk_len_10__f_agg_\"var\"",
    "value__autocorrelation__lag_1", "value__agg_linear_trend__attr_\"slope\"__chunk_len_50__f_agg_\"var\"",
    "value__time_reversal_asymmetry_statistic__lag_1", "value__first_location_of_maximum",
    "value__agg_linear_trend__attr_\"slope\"__chunk_len_10__f_agg_\"var\"", "value__partial_autocorrelation__lag_1",
    "value__time_reversal_asymmetry_statistic__lag_2", "value__agg_linear_trend__attr_\"stderr\"__chunk_len_50__f_agg_\"var\"",
    "value__fft_coefficient__attr_\"imag\"__coeff_6", "value__approximate_entropy__m_2__r_0.7",
    "value__agg_linear_trend__attr_\"intercept\"__chunk_len_10__f_agg_\"var\"",
]

# tsfresh import
try:
    import tsfresh
    from tsfresh.feature_extraction import extract_features, settings
except ImportError:
    tsfresh = None

# tsfel import with PRUNED CONFIG
try:
    import tsfel
    NEEDED_TSFEL_FEATURES = {
        "Max", "Min", "Skewness", "Kurtosis", "Variance",
        "Mean diff", "Peak to peak distance",
        "Spectral centroid", "Spectral decrease", "Spectral slope",
        "Spectrogram mean coefficient",
        "Wavelet variance", "Wavelet standard deviation",
    }
    TSFEL_CFG = tsfel.get_features_by_domain()
    for domain in list(TSFEL_CFG.keys()):
        for feat_name in list(TSFEL_CFG[domain].keys()):
            if feat_name not in NEEDED_TSFEL_FEATURES:
                TSFEL_CFG[domain][feat_name]["use"] = "no"
except ImportError:
    tsfel = None
    TSFEL_CFG = None


def load_benchmark_data():
    global OT_LABELS_PATH, OT_DATA_DIR, USB_DIR
    if not os.path.exists(OT_LABELS_PATH):
        # try prepending python/p6
        prefix = "python/p6/"
        if os.path.exists(prefix + OT_LABELS_PATH):
            OT_LABELS_PATH = prefix + OT_LABELS_PATH
            OT_DATA_DIR = prefix + OT_DATA_DIR
            USB_DIR = prefix + USB_DIR
        else:
            print(f"Error: {OT_LABELS_PATH} not found.")
            return None

    ot_labels = pd.read_csv(OT_LABELS_PATH).set_index("file_name")["true_ta_angle"].to_dict()

    data = []
    files = [f for f in os.listdir(OT_DATA_DIR) if f.endswith('.csv')]
    print(f"Loading {len(files)} files from {OT_DATA_DIR}...")

    for f in files:
        if f not in ot_labels:
            continue

        file_path = os.path.join(OT_DATA_DIR, f)
        df = pd.read_csv(file_path)
        df = utils.normalize_columns(df)

        if not all(col in df.columns for col in utils.INPUT_FEATURES + [utils.TARGET_COLUMN]):
            continue

        data.append({
            "df": df,
            "target": ot_labels[f],
            "file_name": f,
        })

    print(f"Loaded {len(data)} files for benchmarking")
    return data[:3]  # Limit to first 3 files for faster benchmarking


def extract_tsfel_features(df_window, feature_list=TOP_FEATURES_TSFEL):
    if tsfel is None:
        return None
    df_tsfel = pd.DataFrame({'torque': df_window["Torque (Nm)"].values})
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        features = tsfel.time_series_features_extractor(
            TSFEL_CFG, df_tsfel, fs=833, verbose=0
        )
    for col in feature_list:
        if col not in features.columns:
            features[col] = 0.0
    return features[feature_list].values


def extract_tsfresh_features(df_window, feature_list=TOP_FEATURES_TSFRESH):
    if tsfresh is None:
        return None
    tsfresh_settings = settings.from_columns(feature_list)
    df_tsfresh = pd.DataFrame({
        'id': [0] * len(df_window),
        'time': range(len(df_window)),
        'value': df_window["Torque (Nm)"].values,
    })
    features = extract_features(
        df_tsfresh, column_id='id', column_sort='time',
        kind_to_fc_parameters=tsfresh_settings,
        disable_progressbar=True, n_jobs=0,
    )
    for col in feature_list:
        if col not in features.columns:
            features[col] = 0.0
    return features[feature_list].values

class DummyScaler:
    def __init__(self, n):
        self.mean_ = np.zeros(n)
        self.scale_ = np.ones(n)
    def transform(self, X):
        return X

def benchmark_model(model_name, model_path, data, feat_type, sub_model_key=None):
    print(f"\nBenchmarking {model_name}...")

    scaler = None
    feature_names = None
    
    # Model loading
    if feat_type == "pytorch":
        model = CNN_LSTM(seq_len=200)
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()
    elif feat_type == "rfint":
        if RFPredictor is None:
            print("RFPredictor not available")
            return None
        # RFPredictor expects a dict model with 'scaler' and 'features'
        # If it's a pkl, we wrap it
        actual_model_path = model_path
        loaded = joblib.load(model_path)
        if not isinstance(loaded, dict):
            # Wrap it
            d = {
                "model": loaded,
                "features": sub_model_key,
                "scaler": DummyScaler(len(sub_model_key))
            }
            actual_model_path = model_path + ".dict.joblib"
            joblib.dump(d, actual_model_path)
        
        # In benchmark we only use Torque (Nm) for these models
        model = RFPredictor(actual_model_path, window_size=200, sub_model_key="model", input_columns=["Torque (Nm)"])
    else:
        if model_path.endswith('.joblib') or model_path.endswith('.pkl'):
            loaded = joblib.load(model_path)
            if isinstance(loaded, dict) and "scaler" in loaded:
                model = loaded.get(sub_model_key, loaded.get("model"))
                scaler = loaded["scaler"]
                feature_names = loaded["features"]
            else:
                model = loaded
                feature_names = sub_model_key # For sliding TSFEL/TSFresh cases
            
            # Force n_jobs=1 for single-sample prediction efficiency
            if hasattr(model, "n_jobs"):
                model.n_jobs = 1

    y_true = []
    y_pred = []
    extraction_times = []
    prediction_times = []

    window_size = 200
    step_size = 50
    max_samples_per_file = 100
    if feat_type == "tsfresh":
        max_samples_per_file = 20 # TSFresh is very slow

    for item in data:
        df = item["df"]
        n_rows = len(df)
        if n_rows < window_size:
            continue
        # Reset sliding state for each file
        extractor = None
        original_to_canon = None
        if feat_type == "sliding":
            # Map features to their canonical names for the extractor
            canonical_features = list(set([canonicalize_feature_name(f) for f in feature_names]))
            extractor = FeatureExtractor(features=canonical_features, columns=["Torque (Nm)"], window_size=window_size)
            # Map each original feature to its canonical name in Rust
            original_to_canon = {f: f"Torque (Nm)_{canonicalize_feature_name(f)}" for f in feature_names}
        elif feat_type == "rfint":
            model.reset()

        samples_count = 0
        for start in range(0, n_rows - window_size + 1, step_size):
            if samples_count >= max_samples_per_file:
                break
            samples_count += 1
            
            # If sliding/rfint, we feed the data since last point
            if feat_type == "sliding" or feat_type == "rfint":
                if start == 0:
                    current_chunk = df.iloc[0 : window_size]
                else:
                    current_chunk = df.iloc[start + window_size - step_size : start + window_size]
            else:
                window = df.iloc[start : start + window_size]

            # 1. Feature extraction / formatting
            try:
                start_ext = time.perf_counter()
                if feat_type == "tsfresh":
                    X = extract_tsfresh_features(window, feature_list=sub_model_key)
                elif feat_type == "tsfel":
                    X = extract_tsfel_features(window, feature_list=sub_model_key)
                elif feat_type == "tsf_raw":
                    X = window["Torque (Nm)"].values.reshape(1, -1)
                elif feat_type == "pytorch":
                    raw_values = window["Torque (Nm)"].values
                    X = torch.tensor(raw_values, dtype=torch.float32).view(1, 1, -1)
                elif feat_type == "sliding":
                    stats = extractor.update(current_chunk)
                    if not stats:
                        continue
                    feat_vals = [stats[original_to_canon[f]] for f in feature_names]
                    X = np.array(feat_vals).reshape(1, -1)
                elif feat_type == "rfint":
                    # Convert chunk to Arrow RecordBatch
                    data_np = current_chunk[["Torque (Nm)"]].values.astype(np.float32)
                    arrays = [pa.array(data_np[:, 0])]
                    batch = pa.RecordBatch.from_arrays(arrays, names=["Torque (Nm)"])
                    pred = model.predict(batch)
                    end_ext = time.perf_counter()
                    # RFINT combined extraction and prediction
                    if pred is not None:
                        prediction_times.append(0) # Combined
                        extraction_times.append(end_ext - start_ext)
                        y_pred.append(pred)
                        current_angle = df.iloc[start + window_size - 1][utils.TARGET_COLUMN]
                        remaining_angle = item["target"] - current_angle
                        y_true.append(max(0, remaining_angle))
                    continue
                end_ext = time.perf_counter()
            except Exception:
                # print(f"Extraction error in {model_name}: {e}")
                continue

            if X is None:
                continue

            extraction_times.append(end_ext - start_ext)

            # 2. Prediction
            try:
                start_pred = time.perf_counter()
                
                if feat_type == "pytorch":
                    with torch.no_grad():
                        pred = model(X).item()
                else:
                    if scaler:
                        X = scaler.transform(X)
                    pred = model.predict(X)[0]
                    
                end_pred = time.perf_counter()
            except Exception:
                # print(f"Prediction error in {model_name}: {e}")
                continue

            prediction_times.append(end_pred - start_pred)

            # Target for this window
            current_angle = df.iloc[start + window_size - 1][utils.TARGET_COLUMN]
            remaining_angle = item["target"] - current_angle
            if remaining_angle < 0:
                remaining_angle = 0

            y_true.append(remaining_angle)
            y_pred.append(pred)

    if not y_true:
        print("No samples benchmarked.")
        return None

    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    avg_ext = np.mean(extraction_times) * 1000  # ms
    avg_pred = np.mean(prediction_times) * 1000  # ms
    avg_total = avg_ext + avg_pred

    return {
        "Model": model_name,
        "MAE": mae,
        "R2": r2,
        "Ext (ms)": avg_ext,
        "Pred (ms)": avg_pred,
        "Total (ms)": avg_total,
    }


def main():
    data = load_benchmark_data()
    if not data:
        return

    # Final test suite:
    # RF TSFEL, RF TSFresh, XGB TSFEL, XGB TSFresh, 
    # RF Sliding TSFEL, RF Sliding TSFresh, 
    # RFINT Sliding TSFEL, RFINT Sliding TSFresh, 
    # TSF Raw, CNN-LSTM
    
    models_to_test = [
        ("RF TSFEL",    os.path.join(USB_DIR, "rf_ot_best_tsfel.pkl"),    "tsfel",   TOP_FEATURES_TSFEL),
        ("RF TSFresh",  os.path.join(USB_DIR, "rf_ot_best_tsfresh.pkl"),  "tsfresh", TOP_FEATURES_TSFRESH),
        ("XGB TSFEL",   os.path.join(USB_DIR, "xgb_ot_best_tsfel.pkl"),   "tsfel",   OLD_TOP_FEATURES_TSFEL),
        ("XGB TSFresh", os.path.join(USB_DIR, "xgb_ot_best_tsfresh.pkl"), "tsfresh", TOP_FEATURES_TSFRESH_XGB),
        
        ("RF Sliding TSFEL",   os.path.join(USB_DIR, "rf_ot_best_tsfel.pkl"),    "sliding", TOP_FEATURES_TSFEL),
        ("RF Sliding TSFresh", os.path.join(USB_DIR, "rf_ot_best_tsfresh.pkl"),  "sliding", TOP_FEATURES_TSFRESH),
        
        ("RFINT Sliding TSFEL",   os.path.join(USB_DIR, "rf_ot_best_tsfel.pkl"),    "rfint",   TOP_FEATURES_TSFEL),
        ("RFINT Sliding TSFresh", os.path.join(USB_DIR, "rf_ot_best_tsfresh.pkl"),  "rfint",   TOP_FEATURES_TSFRESH),
        
        ("TSF Raw",     os.path.join(USB_DIR, "tsf_ot_best_raw.pkl"),     "tsf_raw", None),
        ("CNN-LSTM",    os.path.join(USB_DIR, "cnn_lstm_finetuned_old.pth"), "pytorch", None),
    ]

    results = []
    for name, path, feat_type, sub_key in models_to_test:
        # Check both USB_DIR and current directory for models
        actual_path = path
        if not os.path.exists(actual_path):
            filename = os.path.basename(path)
            if os.path.exists(filename):
                actual_path = filename
        
        if os.path.exists(actual_path):
            try:
                res = benchmark_model(name, actual_path, data, feat_type, sub_key)
                if res:
                    results.append(res)
            except Exception as e:
                print(f"Error benchmarking {name}: {e}")
        else:
            print(f"Skipping {name}, file not found: {actual_path}")

    if results:
        res_df = pd.DataFrame(results)
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS (REGRESSION)")
        print("=" * 80)
        print(res_df.to_string(index=False))
        print("=" * 80)


if __name__ == "__main__":
    main()
