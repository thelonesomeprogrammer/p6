import pandas as pd

# Centralized constants to prevent mismatches
COLUMNS_MAPPING = {
    "Torque (Nm)": "Torque (Nm)",
    "Torque(Nm)": "Torque (Nm)",
    "Current (V)": "Current (V)",
    "Current(V)": "Current (V)",
    "Angle (deg)": "Angle (deg)",
    "Angle(°)": "Angle (deg)",
    "Angle(deg)": "Angle (deg)",
    "Depth (mm)": "Depth (mm)",
    "Depth(mm)": "Depth (mm)",
    "Nset (1/min)": "Nset (1/min)",
    "Nset(1/min)": "Nset (1/min)",
    "Time (ms)": "Time (ms)",
    "Time(ms)": "Time (ms)",
}

# The canonical features we use for training
INPUT_FEATURES = ["Torque (Nm)", "Current (V)"]
TARGET_COLUMN = "Angle (deg)"

# Sampling parameters for LSTM to ensure training/inference alignment
LSTM_STEP_SIZE = 100  # Process every 100 rows
LSTM_SEQ_LEN = 20     # Sequence length

def normalize_columns(df):
    """Normalize DataFrame columns to standard names."""
    df = df.copy()
    new_cols = {}
    for col in df.columns:
        if col in COLUMNS_MAPPING:
            new_cols[col] = COLUMNS_MAPPING[col]
    return df.rename(columns=new_cols)
