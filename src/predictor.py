import numpy as np
import joblib
import os
import warnings

class MLPredictor:
    def __init__(self, model_type="rf", model_path="src/predictors_ml.joblib"):
        """
        model_type: "rf" for Random Forest, "gb" for Gradient Boosting
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Please run src/train_ml.py first.")
        
        all_models = joblib.load(model_path)
        if model_type not in all_models:
            raise ValueError(f"Model type {model_type} not found in {model_path}. Available: {list(all_models.keys())}")
            
        data = all_models[model_type]
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["features"]
        self.labels = data["labels"]
        self.features = ["Torque (Nm)", "Current (V)", "Depth (mm)"]

    def extract_features(self, df):
        """Extract statistical features from a window of data."""
        stats = {}
        
        # Normalize column names for searching
        # Handle "(deg)" and "(°)" interchangeably
        norm_cols = {}
        for c in df.columns:
            nc = c.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            norm_cols[nc] = c

        for col_name in self.features:
            # Normalized version of what we are looking for
            search_key = col_name.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            
            if search_key not in norm_cols:
                # Fill missing columns with 0
                for stat in ["mean", "std", "max", "min", "last", "median", "slope"]:
                    stats[f"{col_name}_{stat}"] = 0
                continue
            
            series = df[norm_cols[search_key]]
            stats[f"{col_name}_mean"] = series.mean()
            stats[f"{col_name}_std"] = series.std() if len(series) > 1 else 0
            stats[f"{col_name}_max"] = series.max()
            stats[f"{col_name}_min"] = series.min()
            stats[f"{col_name}_last"] = series.iloc[-1]
            stats[f"{col_name}_median"] = series.median()
            
            if len(series) > 1:
                stats[f"{col_name}_slope"] = (series.iloc[-1] - series.iloc[0]) / len(series)
            else:
                stats[f"{col_name}_slope"] = 0
        
        # Ensure features are in the correct order as seen by the model
        feature_vector = [stats[name] for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def predict(self, df_window):
        """
        Predict label for an expanding window of KXML data.
        """
        if len(df_window) < 2:
            return None
            
        X = self.extract_features(df_window)
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
    def __init__(self, model_type="rf_regressor", model_path="src/regressors_ml.joblib"):
        """
        model_type: "rf_regressor", "gb_regressor", or "lr_regressor"
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file {model_path} not found. Please run src/train_regression.py first.")
        
        all_models = joblib.load(model_path)
        if model_type not in all_models:
            raise ValueError(f"Model type {model_type} not found in {model_path}. Available: {list(all_models.keys())}")
            
        data = all_models[model_type]
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.feature_names = data["features"]
        self.features = ["Torque (Nm)", "Current (V)", "Depth (mm)", "Angle (deg)"]

    def extract_features(self, df):
        """Extract statistical features from a window of data."""
        stats = {}
        
        # Normalize column names for searching
        # Handle "(deg)" and "(°)" interchangeably
        norm_cols = {}
        for c in df.columns:
            nc = c.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            norm_cols[nc] = c

        for col_name in self.features:
            # Normalized version of what we are looking for
            search_key = col_name.lower().replace(" ", "").replace("(deg)", "").replace("(°)", "").replace("(nm)", "").replace("(v)", "").replace("(mm)", "").replace("(1/min)", "").replace("(ms)", "")
            
            if search_key not in norm_cols:
                # Fill missing columns with 0
                for stat in ["mean", "std", "max", "min", "last", "median", "slope"]:
                    stats[f"{col_name}_{stat}"] = 0
                continue
            
            series = df[norm_cols[search_key]]
            stats[f"{col_name}_mean"] = series.mean()
            stats[f"{col_name}_std"] = series.std() if len(series) > 1 else 0
            stats[f"{col_name}_max"] = series.max()
            stats[f"{col_name}_min"] = series.min()
            stats[f"{col_name}_last"] = series.iloc[-1]
            stats[f"{col_name}_median"] = series.median()
            
            if len(series) > 1:
                stats[f"{col_name}_slope"] = (series.iloc[-1] - series.iloc[0]) / len(series)
            else:
                stats[f"{col_name}_slope"] = 0
        
        # Ensure features are in the correct order as seen by the model
        feature_vector = [stats[name] for name in self.feature_names]
        return np.array(feature_vector).reshape(1, -1)

    def predict(self, df_window):
        """
        Predict remaining angle for an expanding window of data.
        """
        if len(df_window) < 2:
            return None
            
        X = self.extract_features(df_window)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            X_scaled = self.scaler.transform(X)
            prediction = self.model.predict(X_scaled)[0]
            
        return {
            "remaining_angle": float(prediction)
        }

class KerasPredictor:
    def __init__(self):
        pass
