import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from extractor import ExpandingFeatureExtractor
from predictor import LSTMModel
from utils import normalize_columns, INPUT_FEATURES, TARGET_COLUMN, LSTM_STEP_SIZE, LSTM_SEQ_LEN

# Constants
DATA_DIR = "prev-data/Dataset/Intrinsic data/N"

class TimeSeriesDataset(Dataset):
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

def load_file_sequences(file_path):
    try:
        df = pd.read_csv(file_path)
        df = normalize_columns(df)
        if not all(col in df.columns for col in INPUT_FEATURES + [TARGET_COLUMN]):
            return None
        
        n_rows = len(df)
        if n_rows < LSTM_STEP_SIZE:
            return None
        
        final_angle = df[TARGET_COLUMN].max()
        extractor = ExpandingFeatureExtractor(columns=INPUT_FEATURES)
        
        file_features = []
        file_targets = []
        
        # Consistent sampling: process every LSTM_STEP_SIZE rows
        for i in range(0, n_rows, LSTM_STEP_SIZE):
            end_idx = min(i + LSTM_STEP_SIZE, n_rows)
            chunk = df.iloc[i:end_idx]
            stats = extractor.update(chunk)
            
            feat_names = sorted(stats.keys())
            feat_vec = [stats[k] for k in feat_names]
            
            file_features.append(feat_vec)
            file_targets.append(final_angle - df[TARGET_COLUMN].iloc[end_idx-1])

        # Create sequences
        sequences = []
        targets = []
        for i in range(LSTM_SEQ_LEN, len(file_features) + 1):
            sequences.append(file_features[i-LSTM_SEQ_LEN:i])
            targets.append(file_targets[i-1])
            
        return np.array(sequences), np.array(targets), feat_names
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Folder {DATA_DIR} does not exist.")
        return
            
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Loading sequences from {len(files)} files...")
    
    # Split by file to prevent leakage
    train_files, test_files = train_test_split(files, test_size=0.2, random_state=42)
    
    def process_files(file_list):
        all_X, all_y = [], []
        feat_names = None
        for f in file_list:
            res = load_file_sequences(os.path.join(DATA_DIR, f))
            if res:
                X, y, names = res
                all_X.append(X)
                all_y.append(y)
                feat_names = names
        if not all_X: return None, None, None
        return np.concatenate(all_X), np.concatenate(all_y), feat_names

    X_train_raw, y_train, feature_names = process_files(train_files)
    X_test_raw, y_test, _ = process_files(test_files)

    if X_train_raw is None:
        print("No data loaded.")
        return

    # Scale data correctly: fit ONLY on training set
    N_tr, L_tr, F_tr = X_train_raw.shape
    N_te, L_te, F_te = X_test_raw.shape
    
    scaler = StandardScaler()
    X_train_flat = X_train_raw.reshape(-1, F_tr)
    X_train_flat_scaled = scaler.fit_transform(X_train_flat)
    X_train = X_train_flat_scaled.reshape(N_tr, L_tr, F_tr)
    
    X_test_flat = X_test_raw.reshape(-1, F_te)
    X_test_flat_scaled = scaler.transform(X_test_flat)
    X_test = X_test_flat_scaled.reshape(N_te, L_te, F_te)
    
    scaler.feature_names_in_ = np.array(feature_names)

    train_loader = DataLoader(TimeSeriesDataset(X_train, y_train), batch_size=32, shuffle=True)
    test_loader = DataLoader(TimeSeriesDataset(X_test, y_test), batch_size=32)

    model = LSTMModel(input_size=F_tr, hidden_size=64, num_layers=2)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    print(f"Training LSTM on {len(X_train)} sequences, validating on {len(X_test)}...")
    
    epochs = 1000
    best_loss = float('inf')
    patience = 15
    counter = 0
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X).squeeze()
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                outputs = model(batch_X).squeeze()
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
        
        avg_train = train_loss/len(train_loader)
        avg_val = val_loss/len(test_loader)
        
        if (epoch + 1) % 5 == 0:
            print(f"Epoch {epoch+1}, Train Loss: {avg_train:.4f}, Val Loss: {avg_val:.4f}")
            
        if avg_val < best_loss:
            best_loss = avg_val
            torch.save({
                'model_state_dict': model.state_dict(),
                'feature_names': feature_names
            }, "lstm_regressor.pth")
            counter = 0
        else:
            counter += 1
            if counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break

    joblib.dump(scaler, "lstm_scaler.joblib")
    print("LSTM Model and Scaler saved.")

if __name__ == "__main__":
    main()
