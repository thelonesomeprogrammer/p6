import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Add the parent directory containing p6 to the Python path
SCRIPT_DIR = Path(__file__).resolve().parent
P6_PARENT_DIR = SCRIPT_DIR.parents[1]  # This gets /home/marrinus/repos/uni/p6/python
sys.path.append(str(P6_PARENT_DIR))

try:
    from p6 import utils
except ImportError as e:
    print(f"Error importing p6.utils: {e}")
    sys.exit(1)

def resample_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Downsample the dataframe to 833Hz (1.2ms intervals)."""
    df_norm = utils.normalize_columns(df)
    
    if "Time (ms)" not in df_norm.columns:
        # Fall back if Time(ms) column is missing or named differently
        # assume index-based time at 1ms steps
        df_norm["Time (ms)"] = np.arange(0.0, len(df_norm))
        
    t_orig = df_norm["Time (ms)"].values
    if len(t_orig) < 2:
        return df_norm

    # 833Hz corresponds to ~1.2ms intervals (1/833.33 seconds)
    t_new = np.arange(t_orig[0], t_orig[-1], 1.2)
    
    resampled_data = {"Time (ms)": t_new}
    for col in df_norm.columns:
        if col == "Time (ms)":
            continue
        try:
            # Linear interpolation
            resampled_data[col] = np.interp(t_new, t_orig, pd.to_numeric(df_norm[col], errors='coerce').values)
        except Exception as e:
            print(f"Warning: Failed to resample column {col}: {e}")
            resampled_data[col] = np.zeros_like(t_new)

    return pd.DataFrame(resampled_data)

def main():
    # Source: p6/prev-data/Dataset/Intrinsic data
    # Target: p6/prev-data/Intrinsic_data_833Hz
    p6_dir = SCRIPT_DIR.parent
    src_base_dir = p6_dir / "prev-data" / "Dataset" / "Intrinsic data"
    dst_base_dir = p6_dir / "prev-data" / "Intrinsic_data_833Hz"

    if not src_base_dir.exists():
        print(f"Error: Source directory {src_base_dir} does not exist.")
        sys.exit(1)

    print(f"Scanning source directory: {src_base_dir}")
    print(f"Saving resampled files to: {dst_base_dir}")

    # Subdirectories we want to process
    subdirs = ["N", "OT", "UT", "NS"]
    
    total_processed = 0
    for subdir in subdirs:
        src_subdir = src_base_dir / subdir
        dst_subdir = dst_base_dir / subdir
        
        if not src_subdir.exists():
            print(f"Warning: Subdirectory {subdir} not found, skipping.")
            continue
            
        csv_files = list(src_subdir.glob("*.csv"))
        print(f"\nProcessing {len(csv_files)} files in category '{subdir}'...")
        
        for csv_file in csv_files:
            dst_file = dst_subdir / csv_file.name
            try:
                df = pd.read_csv(csv_file)
                df_resampled = resample_dataframe(df)
                
                # Ensure destination folder exists
                dst_subdir.mkdir(parents=True, exist_ok=True)
                df_resampled.to_csv(dst_file, index=False)
                total_processed += 1
                
                if total_processed % 50 == 0:
                    print(f"Processed {total_processed} files...")
            except Exception as e:
                print(f"Error processing {csv_file.name}: {e}")

    print(f"\nCompleted! Downsampled {total_processed} files to 833Hz successfully.")

if __name__ == "__main__":
    main()
