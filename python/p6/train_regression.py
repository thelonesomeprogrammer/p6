import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

from extractor import ExpandingFeatureExtractor

# Constants
DATA_DIR = "prev-data/Dataset/Intrinsic data/N/"
FEATURES = ["Torque (Nm)", "Current (V)"]

def load_data():
    all_samples = []
    
    if not os.path.exists(DATA_DIR):
        print(f"Error: Folder {DATA_DIR} does not exist.")
        return []
            
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Loading {len(files)} files from {DATA_DIR} for regression...")
    
    for file in files:
        file_path = os.path.join(DATA_DIR, file)
        try:
            df = pd.read_csv(file_path)
            # Ensure all needed columns are present
            if not all(col in df.columns for col in FEATURES):
                continue
                
            n_rows = len(df)
            if n_rows < 10:
                continue
            
            final_angle = df['Angle (deg)'].max()
            
            # Each file gets its own extractor
            extractor = ExpandingFeatureExtractor()
            
            # Sample multiple windows from each file
            # We use more granular steps for regression to capture the approach
            last_idx = 0
            for percent in [0.1 ,0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                idx = int(n_rows * percent)
                if idx - last_idx < 1:
                    continue
                
                chunk = df.iloc[last_idx:idx]
                features = extractor.update(chunk)
                
                # Get the last angle from the extracted features
                current_angle = df['Angle (deg)'].iloc[idx - 1]
                remaining_angle = final_angle - current_angle
                
                all_samples.append({
                    "features": features,
                    "target": remaining_angle,
                    "file": file
                })
                last_idx = idx
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            pass
                
    return all_samples

def main():
    print("Starting data loading and feature extraction for regression...")
    data = load_data()
    
    if not data:
        print("No data found.")
        return

    # Convert to DataFrame
    X = pd.DataFrame([d["features"] for d in data]).fillna(0)
    y = np.array([d["target"] for d in data])
    files = [d["file"] for d in data]

    # Split by file to prevent leakage - identifying unique files
    unique_files = list(set(files))
    train_files, test_files = train_test_split(unique_files, test_size=0.2, random_state=42)
    
    train_mask = [f in train_files for f in files]
    test_mask = [f in test_files for f in files]
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"Extracted {len(X_train)} training samples and {len(X_test)} test samples.")
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = {}

    # Model 1: Random Forest Regressor
    print("\nTraining RandomForestRegressor...")
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train_scaled, y_train)
    y_pred_rf = rf.predict(X_test_scaled)
    print(f"RF MAE: {mean_absolute_error(y_test, y_pred_rf):.4f}")
    print(f"RF R2: {r2_score(y_test, y_pred_rf):.4f}")
    results["rf_regressor"] = {
        "model": rf,
        "scaler": scaler,
        "features": list(X.columns)
    }

    # Model 2: Gradient Boosting Regressor
    print("\nTraining GradientBoostingRegressor...")
    gb = GradientBoostingRegressor(n_estimators=100, random_state=42)
    gb.fit(X_train_scaled, y_train)
    y_pred_gb = gb.predict(X_test_scaled)
    print(f"GB MAE: {mean_absolute_error(y_test, y_pred_gb):.4f}")
    print(f"GB R2: {r2_score(y_test, y_pred_gb):.4f}")
    results["gb_regressor"] = {
        "model": gb,
        "scaler": scaler,
        "features": list(X.columns)
    }

    # Model 3: Linear Regression
    print("\nTraining LinearRegression...")
    lr = LinearRegression()
    lr.fit(X_train_scaled, y_train)
    y_pred_lr = lr.predict(X_test_scaled)
    print(f"LR MAE: {mean_absolute_error(y_test, y_pred_lr):.4f}")
    print(f"LR R2: {r2_score(y_test, y_pred_lr):.4f}")
    results["lr_regressor"] = {
        "model": lr,
        "scaler": scaler,
        "features": list(X.columns)
    }
    
    # Save the models
    joblib.dump(results, "regressors_ml.joblib")
    print("\nModels saved to p6/regressors_ml.joblib")

if __name__ == "__main__":
    main()
