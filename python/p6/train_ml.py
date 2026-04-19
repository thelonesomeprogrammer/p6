import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler

from extractor import ExpandingFeatureExtractor

# Constants
DATA_DIR = "prev-data/Dataset/Intrinsic data"
FOLDERS_TO_LABELS = {
    "N": "N",
    "UT": "UT",
    "OT": "OT",
    "NS": "M"
}
IGNORE_FOLDERS = ["P"]
FEATURES = ["Torque (Nm)", "Current (V)"]

def load_data():
    all_samples = []
    
    for folder, label in FOLDERS_TO_LABELS.items():
        folder_path = os.path.join(DATA_DIR, folder)
        if not os.path.exists(folder_path):
            print(f"Warning: Folder {folder_path} does not exist. Skipping.")
            continue
            
        files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        print(f"Loading {len(files)} files from {folder} as label {label}...")
        
        for file in files:
            file_path = os.path.join(folder_path, file)
            try:
                df = pd.read_csv(file_path)
                df = df[FEATURES]
                
                n_rows = len(df)
                if n_rows < 5:
                    continue
                
                # Each file gets its own extractor
                extractor = ExpandingFeatureExtractor()
                
                # Each file gets its own list of windowed samples
                file_samples = []
                last_idx = 0
                for percent in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                    idx = int(n_rows * percent)
                    if idx - last_idx < 1:
                        continue
                        
                    chunk = df.iloc[last_idx:idx]
                    features = extractor.update(chunk)
                    file_samples.append(features)
                    last_idx = idx
                
                all_samples.append({
                    "samples": file_samples,
                    "label": label,
                    "file": file
                })
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
    return all_samples

def main():
    print("Starting data loading and feature extraction...")
    data = load_data()
    
    # Split by file to prevent leakage
    train_data, test_data = train_test_split(data, test_size=0.2, random_state=42, stratify=[d["label"] for d in data])
    
    def flatten_data(subset):
        X = []
        y = []
        for item in subset:
            for sample in item["samples"]:
                X.append(sample)
                y.append(item["label"])
        return pd.DataFrame(X).fillna(0), np.array(y)

    X_train, y_train = flatten_data(train_data)
    X_test, y_test = flatten_data(test_data)
    
    print(f"Extracted {len(X_train)} training samples and {len(X_test)} test samples.")
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Model 1: Random Forest
    print("\nTraining RandomForestClassifier...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train_scaled, y_train)
    y_pred_rf = rf.predict(X_test_scaled)
    print("Random Forest Accuracy:", accuracy_score(y_test, y_pred_rf))
    print(classification_report(y_test, y_pred_rf))
    
    # Model 2: Gradient Boosting
    print("\nTraining GradientBoostingClassifier...")
    gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    gb.fit(X_train_scaled, y_train)
    y_pred_gb = gb.predict(X_test_scaled)
    print("Gradient Boosting Accuracy:", accuracy_score(y_test, y_pred_gb))
    print(classification_report(y_test, y_pred_gb))
    
    # Save the models
    models = {
        "rf": {
            "model": rf,
            "scaler": scaler,
            "features": list(X_train.columns),
            "labels": rf.classes_.tolist()
        },
        "gb": {
            "model": gb,
            "scaler": scaler,
            "features": list(X_train.columns),
            "labels": gb.classes_.tolist()
        }
    }
    joblib.dump(models, "predictors_ml.joblib")
    print("\nModels saved to p6/predictors_ml.joblib")

if __name__ == "__main__":
    main()
