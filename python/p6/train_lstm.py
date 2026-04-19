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

# Constants
DATA_DIR = "prev-data/Dataset/Intrinsic data/N"
FEATURES = ["Torque (Nm)", "Current (V)"]
SEQ_LEN = 20

class TimeSeriesDataset(Dataset):
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

def load_sequences():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Folder {DATA_DIR} does not exist.")
        return [], []
            
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Loading sequences from {len(files)} files...")
    
    all_features = []
    all_targets = []
    
    # We'll use this to fit the scaler first
    feature_vectors = []

    for (idx, file) in enumerate(files):
        file_path = os.path.join(DATA_DIR, file)
        try:
            df = pd.read_csv(file_path)
            if not all(col in df.columns for col in FEATURES):
                continue
            
            n_rows = len(df)
            if n_rows < 20:
                continue
            
            final_angle = df['Angle (deg)'].max()
            extractor = ExpandingFeatureExtractor(
            )
            
            file_features = []
            file_targets = []
            
            # Step through the file to create a sequence of feature states
            # For LSTM we want more frequent updates
            for i in range(100, n_rows, 100):
                chunk = df.iloc[i-5:i]
                stats = extractor.update(chunk)
                
                feat_names = sorted(stats.keys())
                feat_vec = [stats[k] for k in feat_names]
                
                file_features.append(feat_vec)
                file_targets.append(final_angle - df['Angle (deg)'].iloc[i-1])
                feature_vectors.append(feat_vec)

            # Create sequences of SEQ_LEN
            for i in range(SEQ_LEN, len(file_features)):
                all_features.append(file_features[i-SEQ_LEN:i])
                all_targets.append(file_targets[i-1])
            print(f"Loaded {len(file_features)} feature states from {file} as number {idx+1} of {len(files)}.     ", end='\r', flush=True)
                    
        except Exception:
            pass

    print(f"Loaded {len(all_features)} sequences.")
                
    return np.array(all_features), np.array(all_targets), feat_names

def train():
    X, y, feature_names = load_sequences()
    if len(X) == 0:
        return

    # Flatten X to scale, then reshape back
    N, L, F = X.shape
    X_flat = X.reshape(-1, F)
    
    scaler = StandardScaler()
    X_flat_scaled = scaler.fit_transform(X_flat)
    X_scaled = X_flat_scaled.reshape(N, L, F)
    scaler.feature_names_in_ = np.array(feature_names)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    train_dataset = TimeSeriesDataset(X_train, y_train)
    test_dataset = TimeSeriesDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32)

    model = LSTMModel(input_size=F, hidden_size=64, num_layers=2)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    print("Training LSTM...")
    epochs = 4000
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
        
        if (epoch + 1) % 5 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {train_loss/len(train_loader):.4f}")

    # Save
    torch.save({
        'model_state_dict': model.state_dict(),
        'feature_names': feature_names
    }, "lstm_regressor.pth")
    joblib.dump(scaler, "lstm_scaler.joblib")
    print("LSTM Model and Scaler saved.")

if __name__ == "__main__":
    train()
