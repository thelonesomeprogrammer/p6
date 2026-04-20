import numpy as np
import joblib
import os
import warnings
import pandas as pd
import torch
import torch.nn as nn
from extractor import ExpandingFeatureExtractor
from utils import normalize_columns, INPUT_FEATURES, LSTM_STEP_SIZE

class MLPredictor:
    def __init__(self, model_type="rf", model_path="predictors_ml.joblib"):
        """
        model_type: "rf" for Random Forest, "gb" for Gradient Boosting
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Please run p6/train_ml.py first.")
        
        all_models = joblib.load(model_path)
        if model_type not in all_models:
            raise ValueError(f"Model type {model_type} not found in {model_path}. Available: {list(all_models.keys())}")
            
        data = all_models[model_type]
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["features"]
        self.labels = data.get("labels", [])
        self.features = INPUT_FEATURES
        
        # Proper expanding state
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def reset(self):
        """Reset the internal state for a new data stream."""
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def extract_features(self, df):
        """Incrementally extract statistical features."""
        if len(df) < self.processed_count:
            self.reset()

        if len(df) <= self.processed_count:
            if self.last_stats is None:
                return None
            return self._format_feature_vector(self.last_stats)

        new_data = df.iloc[self.processed_count:]
        mapped_df = normalize_columns(new_data)[self.features]
        
        self.last_stats = self.extractor.update(mapped_df)
        self.processed_count = len(df)
        
        return self._format_feature_vector(self.last_stats)

    def _format_feature_vector(self, stats):
        feature_vector = [stats.get(name, 0.0) for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def predict(self, df_window):
        if len(df_window) < 2:
            return None
            
        X = self.extract_features(df_window)
        if X is None:
            return None

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_scaled = self.scaler.transform(X)
            prediction = self.model.predict(X_scaled)[0]
            probs = self.model.predict_proba(X_scaled)[0]
            
        prob_dict = {label: float(prob) for label, prob in zip(self.model.classes_, probs)}
        
        return {
            "prediction": str(prediction),
            "probabilities": prob_dict
        }

class RegressionPredictor:
    def __init__(self, model_type="rf_regressor", model_path="regressors_ml.joblib"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Please run p6/train_regression.py first.")
        
        all_models = joblib.load(model_path)
        if model_type not in all_models:
            raise ValueError(f"Model type {model_type} not found in {model_path}. Available: {list(all_models.keys())}")
            
        data = all_models[model_type]
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["features"]
        self.features = INPUT_FEATURES
        
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def reset(self):
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def extract_features(self, df):
        if len(df) < self.processed_count:
            self.reset()

        if len(df) <= self.processed_count:
            if self.last_stats is None:
                return None
            return self._format_feature_vector(self.last_stats)

        new_data = df.iloc[self.processed_count:]
        mapped_df = normalize_columns(new_data)[self.features]
        
        self.last_stats = self.extractor.update(mapped_df)
        self.processed_count = len(df)
        
        return self._format_feature_vector(self.last_stats)

    def _format_feature_vector(self, stats):
        feature_vector = [stats.get(name, 0.0) for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def predict(self, df_window):
        if len(df_window) < 2:
            return None
            
        X = self.extract_features(df_window)
        if X is None:
            return None

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_scaled = self.scaler.transform(X)
            prediction = self.model.predict(X_scaled)[0]
            
        return {
            "remaining_angle": float(prediction)
        }

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out

class LSTMPredictor:
    def __init__(self, model_path=None, scaler_path=None):
        self.features = INPUT_FEATURES
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.feature_history = []
        self.max_history = 50
        
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "lstm_regressor.pth")
        if scaler_path is None:
            scaler_path = os.path.join(os.path.dirname(__file__), "lstm_scaler.joblib")
            
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
            self.feature_names = self.scaler.feature_names_in_.tolist()
            input_size = len(self.feature_names)
            
            self.model = LSTMModel(input_size=input_size)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
        else:
            self.model = None
            self.scaler = None
            print(f"Warning: LSTM model files not found at {model_path}")

    def reset(self):
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.feature_history = []

    def predict(self, df_window):
        if self.model is None or len(df_window) < 2:
            return None

        if len(df_window) < self.processed_count:
            self.reset()

        # ONLY update when we have a full chunk of LSTM_STEP_SIZE new rows
        # to match the training temporal sampling logic
        if len(df_window) >= self.processed_count + LSTM_STEP_SIZE:
            # Process in chunks of LSTM_STEP_SIZE
            while len(df_window) >= self.processed_count + LSTM_STEP_SIZE:
                chunk = df_window.iloc[self.processed_count : self.processed_count + LSTM_STEP_SIZE]
                mapped_df = normalize_columns(chunk)[self.features]
                stats = self.extractor.update(mapped_df)
                self.processed_count += LSTM_STEP_SIZE
                
                feat_vec = [stats.get(name, 0.0) for name in self.feature_names]
                self.feature_history.append(feat_vec)
                if len(self.feature_history) > self.max_history:
                    self.feature_history.pop(0)

        if not self.feature_history:
            return None

        seq = np.array(self.feature_history)
        seq_scaled = self.scaler.transform(seq)
        X = torch.FloatTensor(seq_scaled).unsqueeze(0)
        
        with torch.no_grad():
            prediction = self.model(X).item()
            
        return {
            "remaining_angle": float(prediction),
            "sequence_len": len(self.feature_history)
        }
