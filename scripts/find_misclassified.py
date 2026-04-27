#!/usr/bin/env python3
"""
Script to find files that were misclassified by the ML classifier with high confidence.
"""
import os
import pandas as pd
import numpy as np
from predictor import MLPredictor
from extractor import ExpandingFeatureExtractor
from utils import normalize_columns, INPUT_FEATURES

# Constants
DATA_DIR = "prev-data/Dataset/Intrinsic data"
FOLDERS_TO_LABELS = {
    "N": "N",
    "UT": "UT",
    "OT": "OT",
    "NS": "M"
}
HIGH_CONFIDENCE_THRESHOLD = 0.4

def load_and_classify_file(file_path, true_label, predictor):
    """
    Load a file, extract features, and classify using the predictor.
    Returns prediction result with confidence.
    """
    try:
        df = pd.read_csv(file_path)
        df = normalize_columns(df)
        
        # Check if features exist after normalization
        if not all(col in df.columns for col in INPUT_FEATURES):
            return None
        
        df = df[INPUT_FEATURES]
        
        # Use the same expanding window approach as training
        n_rows = len(df)
        if n_rows < 5:
            return None
        
        extractor = ExpandingFeatureExtractor()
        
        # Get prediction at 100% (final state)
        last_idx = 0
        for percent in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            idx = int(n_rows * percent)
            if idx - last_idx < 1:
                continue
                
            chunk = df.iloc[last_idx:idx]
            features = extractor.update(chunk)
            last_idx = idx
        
        # Make prediction
        X = pd.DataFrame([features]).fillna(0)
        X_scaled = predictor.scaler.transform(X)
        prediction = predictor.model.predict(X_scaled)[0]
        probs = predictor.model.predict_proba(X_scaled)[0]
        max_prob = np.max(probs)
        
        return {
            "prediction": prediction,
            "true_label": true_label,
            "max_prob": max_prob,
            "probabilities": {label: float(prob) for label, prob in zip(predictor.model.classes_, probs)},
            "misclassified": prediction != true_label
        }
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

import matplotlib.pyplot as plt
import shutil

# ... existing code ...

def plot_torque_curve(file_path, result):
    """Plot the torque curve for a given file."""
    try:
        df = pd.read_csv(file_path)
        df = normalize_columns(df)
        
        plt.figure(figsize=(10, 6))
        plt.plot(df["Time (ms)"], df["Torque (Nm)"], label="Torque")
        plt.title(f"File: {result['folder']}/{result['file']}\n"
                  f"True: {result['true_label']}, Pred: {result['prediction']} ({result['max_prob']:.2f})")
        plt.xlabel("Time (ms)")
        plt.ylabel("Torque (Nm)")
        plt.grid(True)
        plt.legend()
        plt.show(block=False)
    except Exception as e:
        print(f"Error plotting {file_path}: {e}")

def interactive_review(misclassified_list):
    """Interactively review misclassified files."""
    if not misclassified_list:
        return

    print("\nStarting interactive review...")
    print("Commands: [m]ove to predicted, [r]emove, [s]kip/leave, [q]uit")
    
    # Reverse mapping for folder names
    LABEL_TO_FOLDER = {v: k for k, v in FOLDERS_TO_LABELS.items()}
    # Special case for NS/M
    LABEL_TO_FOLDER["M"] = "NS"

    for i, result in enumerate(misclassified_list):
        print(f"\nReviewing {i+1}/{len(misclassified_list)}: {result['folder']}/{result['file']}")
        print(f"True Label: {result['true_label']}, Predicted: {result['prediction']} (Conf: {result['max_prob']:.4f})")
        
        plot_torque_curve(result['full_path'], result)
        
        choice = input("Action [m/r/s/q]: ").lower().strip()
        plt.close()

        if choice == 'q':
            break
        elif choice == 'm':
            target_folder = LABEL_TO_FOLDER.get(result['prediction'])
            if target_folder:
                target_path = os.path.join(DATA_DIR, target_folder, result['file'])
                print(f"Moving to {target_path}...")
                shutil.move(result['full_path'], target_path)
            else:
                print(f"Error: Could not find folder for label {result['prediction']}")
        elif choice == 'r':
            print(f"Removing {result['full_path']}...")
            os.remove(result['full_path'])
        elif choice == 's':
            print("Skipping...")
            continue
        else:
            print("Unknown command, skipping...")

def main():
    print("Finding misclassified files with high confidence...")
    print(f"High confidence threshold: {HIGH_CONFIDENCE_THRESHOLD}")
    
    # Initialize predictor
    try:
        predictor = MLPredictor(model_type="rf", model_path="predictors_ml.joblib")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    misclassified_high_confidence = []
    all_classifications = []
    
    # Process each folder
    for folder, true_label in FOLDERS_TO_LABELS.items():
        folder_path = os.path.join(DATA_DIR, folder)
        if not os.path.exists(folder_path):
            print(f"Warning: Folder {folder_path} does not exist. Skipping.")
            continue
        
        files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        print(f"\nProcessing {len(files)} files from {folder} (true label: {true_label})...")
        
        for file in files:
            file_path = os.path.join(folder_path, file)
            result = load_and_classify_file(file_path, true_label, predictor)
            
            if result:
                result["file"] = file
                result["folder"] = folder
                result["full_path"] = file_path
                all_classifications.append(result)
                
                # Check if misclassified
                if result["misclassified"]:
                    misclassified_high_confidence.append(result)
    
    # Sort by confidence descending
    misclassified_high_confidence.sort(key=lambda x: x['max_prob'], reverse=True)

    # Print results
    print("\n" + "="*80)
    print(f"Total files processed: {len(all_classifications)}")
    print(f"Total misclassified: {len(misclassified_high_confidence)}")
    print("="*80)
    
    if misclassified_high_confidence:
        interactive_review(misclassified_high_confidence)
    else:
        print("\nNo files were misclassified!")
    
    # Optional: Print overall statistics
    print("\n" + "="*80)
    print("Overall Classification Statistics:")
    print("-"*80)
    
    # Count by true label
    for label in FOLDERS_TO_LABELS.values():
        label_files = [r for r in all_classifications if r['true_label'] == label]
        misclassified = [r for r in label_files if r['true_label'] == label and r['misclassified']]
        print(f"\nLabel {label}:")
        print(f"  Total: {len(label_files)}")
        print(f"  Correct: {len(label_files) - len(misclassified)}")
        print(f"  Misclassified: {len(misclassified)}")
        
        if misclassified:
            avg_confidence = np.mean([r['max_prob'] for r in misclassified])
            print(f"  Avg confidence when wrong: {avg_confidence:.4f}")

if __name__ == "__main__":
    main()
