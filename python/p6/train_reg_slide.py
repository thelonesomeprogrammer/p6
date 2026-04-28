import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

# Local imports
from . import utils
from .extractor import ExpandingFeatureExtractor

# Constants
OT_DATA_DIR = "prev-data/OT_truncated_intrinsic_833Hz/"
OT_LABELS_PATH = "prev-data/ot_labels.csv"
WINDOW_SIZE = 200
STEP_SIZE = 50

def load_data():
    if not os.path.exists(OT_LABELS_PATH):
        print(f"Error: {OT_LABELS_PATH} not found.")
        return None

    ot_labels = pd.read_csv(OT_LABELS_PATH).set_index("file_name")["true_ta_angle"].to_dict()
    
    files = [f for f in os.listdir(OT_DATA_DIR) if f.endswith('.csv') and f in ot_labels]
    print(f"Loading {len(files)} files for sliding window regression...")
    
    all_samples = []

    for file in tqdm(files):
        file_path = os.path.join(OT_DATA_DIR, file)
        try:
            df = pd.read_csv(file_path)
            df = utils.normalize_columns(df)
            
            if not all(col in df.columns for col in utils.INPUT_FEATURES + [utils.TARGET_COLUMN]):
                continue
            
            final_angle = ot_labels[file]
            n_rows = len(df)
            
            if n_rows < WINDOW_SIZE:
                continue

            extractor = ExpandingFeatureExtractor()
            
            # Extract features for all windows in this file
            for start in range(0, n_rows - WINDOW_SIZE + 1, STEP_SIZE):
                end = start + WINDOW_SIZE
                window = df.iloc[start:end]
                
                extractor.reset()
                feat_dict = extractor.update(window)
                
                current_angle = window[utils.TARGET_COLUMN].iloc[-1]
                remaining_angle = final_angle - current_angle
                
                if remaining_angle < 0:
                    remaining_angle = 0
                
                all_samples.append({
                    "features": feat_dict,
                    "target": remaining_angle,
                    "file": file
                })
                
        except Exception as e:
            print(f"Error processing {file}: {e}")
            
    return all_samples

def main():
    print("Starting data loading and feature extraction...")
    data = load_data()
    
    if not data:
        print("No data found.")
        return

    # Convert features to DataFrame to align columns
    X_df = pd.DataFrame([d["features"] for d in data]).fillna(0)
    X = X_df.values
    y = np.array([d["target"] for d in data])
    files = [d["file"] for d in data]
    feature_names = list(X_df.columns)

    # Split by file to prevent leakage
    unique_files = list(set(files))
    train_files, test_files = train_test_split(unique_files, test_size=0.2, random_state=42)
    
    train_mask = [f in train_files for f in files]
    test_mask = [f in test_files for f in files]
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Random Forest
    print("\nTraining Random Forest...")
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train)
    y_pred_rf = rf.predict(X_test_scaled)
    print(f"RF MAE: {mean_absolute_error(y_test, y_pred_rf):.4f}")
    print(f"RF R2: {r2_score(y_test, y_pred_rf):.4f}")
    
    # XGBoost
    print("\nTraining XGBoost...")
    xgb = XGBRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    xgb.fit(X_train_scaled, y_train)
    y_pred_xgb = xgb.predict(X_test_scaled)
    print(f"XGB MAE: {mean_absolute_error(y_test, y_pred_xgb):.4f}")
    print(f"XGB R2: {r2_score(y_test, y_pred_xgb):.4f}")
    
    # Save models
    results = {
        "rf": rf,
        "xgb": xgb,
        "scaler": scaler,
        "features": feature_names
    }
    joblib.dump(results, "regressors_slide.joblib")
    print("\nModels saved to regressors_slide.joblib")

if __name__ == "__main__":
    main()
