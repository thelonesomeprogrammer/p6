import numpy as np
import joblib
import os
import warnings
import pandas as pd
import torch
import torch.nn as nn
from .extractor import ExpandingFeatureExtractor

class MLPredictor:
    def __init__(self, model_type="rf", model_path="p6/predictors_ml.joblib"):
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
        self.features = ["Torque (Nm)", "Current (V)"]
        
        # Proper expanding state
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def reset(self):
        """Reset the internal state for a new data stream."""
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def _get_mapped_df(self, df):
        # Normalize column names for searching
        norm_cols = {}
        for c in df.columns:
            nc = c.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            norm_cols[nc] = c

        # Map available columns to expected features
        mapped_df = pd.DataFrame(index=df.index)
        for col_name in self.features:
            search_key = col_name.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            
            if search_key in norm_cols:
                mapped_df[col_name] = df[norm_cols[search_key]]
            else:
                mapped_df[col_name] = 0.0
        return mapped_df

    def extract_features(self, df):
        """Incrementally extract statistical features."""
        # Auto-reset if we detect a new/shorter sequence
        if len(df) < self.processed_count:
            self.reset()

        if len(df) <= self.processed_count:
            if self.last_stats is None:
                return None
            return self._format_feature_vector(self.last_stats)

        new_data = df.iloc[self.processed_count:]
        mapped_df = self._get_mapped_df(new_data)
        
        self.last_stats = self.extractor.update(mapped_df)
        self.processed_count = len(df)
        
        return self._format_feature_vector(self.last_stats)

    def _format_feature_vector(self, stats):
        feature_vector = [stats.get(name, 0.0) for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def predict(self, df_window):
        """
        Predict label for an expanding window of KXML data.
        """
        if len(df_window) < 2:
            return None
            
        X = self.extract_features(df_window)
        if X is None:
            return None

        # Suppress feature name warning from sklearn
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
    def __init__(self, model_type="rf_regressor", model_path="p6/regressors_ml.joblib"):
        """
        model_type: "rf_regressor", "gb_regressor", or "lr_regressor"
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Please run p6/train_regression.py first.")
        
        all_models = joblib.load(model_path)
        if model_type not in all_models:
            raise ValueError(f"Model type {model_type} not found in {model_path}. Available: {list(all_models.keys())}")
            
        data = all_models[model_type]
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["features"]
        self.features = ["Torque (Nm)", "Current (V)"]
        
        # Proper expanding state
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def reset(self):
        """Reset the internal state for a new data stream."""
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.last_stats = None

    def _get_mapped_df(self, df):
        # Normalize column names for searching
        norm_cols = {}
        for c in df.columns:
            nc = c.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            norm_cols[nc] = c

        # Map available columns to expected features
        mapped_df = pd.DataFrame(index=df.index)
        for col_name in self.features:
            search_key = col_name.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            
            if search_key in norm_cols:
                mapped_df[col_name] = df[norm_cols[search_key]]
            else:
                mapped_df[col_name] = 0.0
        return mapped_df

    def extract_features(self, df):
        """Incrementally extract statistical features."""
        # Auto-reset if we detect a new/shorter sequence
        if len(df) < self.processed_count:
            self.reset()

        if len(df) <= self.processed_count:
            if self.last_stats is None:
                return None
            return self._format_feature_vector(self.last_stats)

        new_data = df.iloc[self.processed_count:]
        mapped_df = self._get_mapped_df(new_data)
        
        self.last_stats = self.extractor.update(mapped_df)
        self.processed_count = len(df)
        
        return self._format_feature_vector(self.last_stats)

    def _format_feature_vector(self, stats):
        feature_vector = [stats.get(name, 0.0) for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def predict(self, df_window):
        """
        Predict remaining angle for an expanding window of data.
        """
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
        # x: (batch, seq_len, input_size)
        out, _ = self.lstm(x)
        # Only take the output from the last time step
        out = self.fc(out[:, -1, :])
        return out

class LSTMPredictor:
    def __init__(self, model_path=None, scaler_path=None):
        self.features = ["Torque (Nm)", "Current (V)"]
        self.extractor = ExpandingFeatureExtractor(columns=self.features)
        self.processed_count = 0
        self.feature_history = []
        self.max_history = 50 # Keep last 50 feature vectors for sequence
        
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "lstm_regressor.pth")
        if scaler_path is None:
            scaler_path = os.path.join(os.path.dirname(__file__), "lstm_scaler.joblib")
            
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
            
            # Extract input_size from features in scaler or checkpoint
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

    def _get_mapped_df(self, df):
        mapped_df = pd.DataFrame(index=df.index)
        for col_name in self.features:
            if col_name in df.columns:
                mapped_df[col_name] = df[col_name]
            else:
                # Try case-insensitive and stripped
                found = False
                for c in df.columns:
                    if c.lower().strip() == col_name.lower().strip():
                        mapped_df[col_name] = df[c]
                        found = True
                        break
                if not found:
                    mapped_df[col_name] = 0.0
        return mapped_df

    def predict(self, df_window):
        if self.model is None or len(df_window) < 2:
            return None

        # Auto-reset if we detect a new/shorter sequence
        if len(df_window) < self.processed_count:
            self.reset()

        # Update features
        if len(df_window) > self.processed_count:
            new_data = df_window.iloc[self.processed_count:]
            mapped_df = self._get_mapped_df(new_data)
            stats = self.extractor.update(mapped_df)
            self.processed_count = len(df_window)
            
            # Format feature vector
            feat_vec = [stats.get(name, 0.0) for name in self.feature_names]
            self.feature_history.append(feat_vec)
            if len(self.feature_history) > self.max_history:
                self.feature_history.pop(0)

        if not self.feature_history:
            return None

        # Prepare sequence for LSTM
        seq = np.array(self.feature_history)
        seq_scaled = self.scaler.transform(seq)
        
        X = torch.FloatTensor(seq_scaled).unsqueeze(0) # Add batch dimension
        
        with torch.no_grad():
            prediction = self.model(X).item()
            
        return {
            "remaining_angle": float(prediction),
            "sequence_len": len(self.feature_history)
        }

