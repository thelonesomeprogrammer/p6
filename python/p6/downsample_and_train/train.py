import sys
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from tqdm import tqdm
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# Add the parent directory containing p6 to the Python path
SCRIPT_DIR = Path(__file__).resolve().parent
P6_PARENT_DIR = SCRIPT_DIR.parents[1]  # /home/marrinus/repos/uni/p6/python
sys.path.append(str(P6_PARENT_DIR))

try:
    from p6 import utils
    from p6.extractor import FeatureExtractor
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Constants
WINDOW_SIZE = 200
STEP_SIZE = 50

# Setup paths robustly
P6_DIR = SCRIPT_DIR.parent
OT_LABELS_PATH = P6_DIR / "prev-data" / "ot_labels.csv"
RESAMPLED_DIR = P6_DIR / "prev-data" / "Intrinsic_data_833Hz"

def extract_features_from_run(torque_arr, angle_arr, file_identifier):
    """Extract sliding window features and target remaining angle for a single run."""
    torque_arr = np.array(torque_arr, dtype=np.float32)
    angle_arr = np.array(angle_arr, dtype=np.float32)
    
    n_rows = len(torque_arr)
    if n_rows < WINDOW_SIZE:
        return []
        
    final_angle = angle_arr.max()
    
    # We wrap torque in a dataframe to feed into the FeatureExtractor
    df_torque = pd.DataFrame({"Torque (Nm)": torque_arr})
    extractor = FeatureExtractor(columns=["Torque (Nm)"], window_size=WINDOW_SIZE)
    
    samples = []
    for start in range(0, n_rows - WINDOW_SIZE + 1, STEP_SIZE):
        end = start + WINDOW_SIZE
        window_df = df_torque.iloc[start:end]
        
        extractor.reset()
        feat_dict = extractor.update(window_df)
        
        if not feat_dict:
            continue
            
        current_angle = angle_arr[end - 1]
        remaining_angle = max(0.0, final_angle - current_angle)
        
        samples.append({
            "features": feat_dict,
            "target": remaining_angle,
            "file": file_identifier
        })
        
    return samples

def load_resampled_prev_data():
    """Load the resampled 833Hz prev data."""
    if not RESAMPLED_DIR.exists():
        print(f"Error: Resampled directory {RESAMPLED_DIR} not found. Please run downsample.py first.")
        return []

    # Load OT labels if available
    ot_labels = {}
    if OT_LABELS_PATH.exists():
        ot_labels = pd.read_csv(OT_LABELS_PATH).set_index("file_name")["true_ta_angle"].to_dict()
        print(f"Loaded {len(ot_labels)} OT labels from {OT_LABELS_PATH}")
    else:
        print(f"Warning: OT labels file not found at {OT_LABELS_PATH}")

    all_samples = []
    
    # We process both N and OT categories
    categories = [("N", False), ("OT", True)]
    
    for category, is_ot in categories:
        cat_dir = RESAMPLED_DIR / category
        if not cat_dir.exists():
            print(f"Warning: Category directory {cat_dir} does not exist. Skipping.")
            continue
            
        csv_files = list(cat_dir.glob("*.csv"))
        print(f"Extracting features from {len(csv_files)} resampled files in category '{category}'...")
        
        for csv_file in tqdm(csv_files):
            try:
                df = pd.read_csv(csv_file)
                df = utils.normalize_columns(df)
                
                if "Torque (Nm)" not in df.columns or "Angle (deg)" not in df.columns:
                    continue
                    
                torque_arr = df["Torque (Nm)"].values
                angle_arr = df["Angle (deg)"].values
                
                if len(torque_arr) < WINDOW_SIZE:
                    continue
                    
                if is_ot:
                    if csv_file.name in ot_labels:
                        final_angle = ot_labels[csv_file.name]
                    else:
                        continue  # Skip OT files without labels
                else:
                    final_angle = angle_arr.max()
                    
                file_samples = extract_features_from_run(torque_arr, angle_arr, f"prev_{category}_{csv_file.name}")
                all_samples.extend(file_samples)
                
            except Exception as e:
                print(f"Error processing {csv_file.name}: {e}")
                
    return all_samples

def load_pyscrew_data():
    """Load the PyScrew s02 dataset and extract features."""
    print("Loading PyScrew 's02' dataset...")
    try:
        import pyscrew
        pyscrew_dataset = pyscrew.get_data(scenario="s02")
    except Exception as e:
        print(f"Error loading pyscrew dataset: {e}")
        return []
        
    torque_runs = pyscrew_dataset["torque_values"]
    angle_runs = pyscrew_dataset["angle_values"]
    n_runs = len(torque_runs)
    
    print(f"Extracting features from {n_runs} PyScrew 's02' runs...")
    all_samples = []
    
    # Process runs
    for i in tqdm(range(n_runs)):
        t_arr = torque_runs[i]
        a_arr = angle_runs[i]
        
        # Extract features
        run_samples = extract_features_from_run(t_arr, a_arr, f"pyscrew_{i}")
        all_samples.extend(run_samples)
        
    return all_samples

def main():
    # 1. Load and process resampled prev data
    prev_samples = load_resampled_prev_data()
    print(f"Extracted {len(prev_samples)} samples from resampled prev dataset.")
    
    # 2. Load and process PyScrew data
    pyscrew_samples = load_pyscrew_data()
    print(f"Extracted {len(pyscrew_samples)} samples from PyScrew dataset.")
    
    combined_samples = prev_samples + pyscrew_samples
    if not combined_samples:
        print("No samples extracted. Exiting.")
        sys.exit(1)
        
    print(f"Total combined samples: {len(combined_samples)}")
    
    # Convert features to DataFrame
    X_df = pd.DataFrame([s["features"] for s in combined_samples]).fillna(0)
    y = np.array([s["target"] for s in combined_samples])
    files = [s["file"] for s in combined_samples]
    feature_names = list(X_df.columns)
    
    X = X_df.values
    
    # 3. Train-test split by file/run to prevent leakage
    unique_files = list(set(files))
    train_files, test_files = train_test_split(unique_files, test_size=0.2, random_state=42)
    
    train_mask = [f in train_files for f in files]
    test_mask = [f in test_files for f in files]
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"Train files: {len(train_files)}, Test files: {len(test_files)}")
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # 4. Standard Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 5. Hyperparameter Optimization via GridSearchCV on a representative subset
    # To keep GridSearch fast on large datasets, we use a 20% subset of train files for tuning
    print("\nSelecting a subset of train files for GridSearch tuning...")
    tuning_files, _ = train_test_split(train_files, test_size=0.8, random_state=42)
    tuning_mask = [f in tuning_files for f in files]
    X_tune = X[tuning_mask]
    y_tune = y[tuning_mask]
    X_tune_scaled = scaler.transform(X_tune)
    print(f"Tuning with {len(tuning_files)} runs ({len(X_tune)} samples)...")
    
    param_grid = {
        'n_estimators': [20, 50, 80, 100, 120, 150, 170, 200, 250, 300],
        'max_depth': [10, 12, 15, 20, 25, 30, None],
        'min_samples_leaf': [1, 2, 4, 6, 8],
        'max_features': ['sqrt', 'log2', None],
    }
    
    print("Running GridSearchCV...")
    rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
    grid_search = GridSearchCV(
        estimator=rf_base,
        param_grid=param_grid,
        cv=3,
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        verbose=2
    )
    grid_search.fit(X_tune_scaled, y_tune)
    
    best_params = grid_search.best_params_
    print(f"\nBest Hyperparameters found: {best_params}")
    print(f"Best CV MAE score: {-grid_search.best_score_:.4f}")
    
    # 6. Train final model on the full training set
    print("\nTraining final model on the full training set...")
    rf_final = RandomForestRegressor(
        n_estimators=best_params['n_estimators'],
        max_depth=best_params['max_depth'],
        min_samples_split=best_params['min_samples_split'],
        random_state=42,
        n_jobs=-1
    )
    rf_final.fit(X_train_scaled, y_train)
    
    # 7. Evaluate on test set
    y_pred = rf_final.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print("\nEvaluation Results on Test Set:")
    print(f"Mean Absolute Error (MAE): {mae:.4f}")
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    print(f"R2 Score: {r2:.4f}")
    
    # 8. Save models
    output_dir = SCRIPT_DIR
    model_save_path = output_dir / "best_rf_regressor.joblib"
    
    results = {
        "model": rf_final,
        "scaler": scaler,
        "features": feature_names,
        "best_params": best_params,
        "metrics": {
            "mae": mae,
            "mse": mse,
            "r2": r2
        }
    }
    
    joblib.dump(results, model_save_path)
    print(f"\nSaved best model and scaler to {model_save_path}")

if __name__ == "__main__":
    main()
