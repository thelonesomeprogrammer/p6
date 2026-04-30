import pyarrow as pa
import numpy as np
from ._p6 import SlidingExtractor as _SlidingExtractor
from . import utils

class FeatureExtractor:
    def __init__(self, features=None, columns=None, window_size=200, stride=1):
        """
        features: List of feature names (e.g., ["mean", "max_value", "std_dev"])
        columns: List of column names to expect in the input batches
        window_size: Size of the sliding window
        stride: Stride of the sliding window
        """
        if features is None:
            self.feature_names = ["total_sum", "mean", "variance", "std", "min", "max", "energy", "rms", "zero_crossing_rate", "mean_abs_change", "mean_change", "cid_ce", "auc", "skewness", "kurtosis"]
        else:
            self.feature_names = features
            
        if columns is None:
            self.columns = utils.INPUT_FEATURES
        else:
            self.columns = columns
            
        self.n_cols = len(self.columns)
        self.window_size = window_size
        self.stride = stride
        
        # Map some common names to Rust internal names if necessary
        name_mapping = {
            "std": "std_dev",
            "max": "max_value",
            "min": "min_value",
            "skewness": "skew",
            "kurtosis": "unbiased_fisher_kurtosis"
        }
        self.rust_to_original = {}
        rust_features = []
        for f in self.feature_names:
            if f == "last":
                continue
            rust_feat = name_mapping.get(f, f)
            rust_features.append(rust_feat)
            self.rust_to_original[rust_feat] = f
            
        self.include_last = "last" in self.feature_names
        self.extractor = _SlidingExtractor(rust_features, self.n_cols, self.window_size, self.stride)
        self.rust_features = rust_features

    def reset(self):
        """Reset the internal Rust extractor state."""
        self.extractor = _SlidingExtractor(self.rust_features, self.n_cols, self.window_size, self.stride)

    def update(self, df):
        """
        Update the extractor with new data from a pandas DataFrame.
        Returns a dictionary containing the extracted features for each column.
        If the window is not yet full, it may return an empty dict or last known stats.
        """
        # Ensure the input DataFrame has the expected columns
        if not all(col in df.columns for col in self.columns):
            missing = [col for col in self.columns if col not in df.columns]
            raise ValueError(f"Input DataFrame must contain columns: {missing}")

        # pull out the relevant columns as numpy arrays and ensure float type
        data = df[self.columns].values.astype(np.float32)
        
        # Create RecordBatch
        arrays = [pa.array(data[:, i]) for i in range(self.n_cols)]
        batch = pa.RecordBatch.from_arrays(arrays, names=self.columns)
        
        # Update Rust extractor
        res_batch = self.extractor.update(batch)
        
        # Convert to pandas to easily iterate
        res_df = res_batch.to_pandas()
        
        if len(res_df) == 0:
            return {}
            
        stats = {}
        # res_df has one row per window per column? 
        # Actually SlidingExtractor.update returns one row per NEW window.
        # If multiple windows were completed, it returns multiple rows?
        # My Rust implementation returns all windows completed in this update.
        # For simplicity, we take the LAST one.
        
        # In SlidingExtractor.update, results are stacked: flat_data.push(slide_res[feat_idx])
        # So it returns n_cols * n_results rows?
        # Let's check Rust code again.
        # results: Vec<ArrayRef> = (0..self.features.len()).map(...)
        # flat_data.push(slide_res[feat_idx]) for col_res in &column_results for slide_res in col_res
        # Yes, it's n_results rows, where each row has features for ALL columns? 
        # No, flat_data is a single column in the RecordBatch.
        # So it has n_cols * n_results elements.
        
        # Wait, if n_cols = 2 and n_results = 3, flat_data has 6 elements.
        # [col0_res0, col0_res1, col0_res2, col1_res0, col1_res1, col1_res2]
        
        n_results = len(res_df) // self.n_cols
        if n_results == 0:
            return {}
            
        # Take the last result for each column
        for i, col_name in enumerate(self.columns):
            row_idx = (i + 1) * n_results - 1
            for rust_feat in self.rust_features:
                orig_feat = self.rust_to_original[rust_feat]
                stats[f"{col_name}_{orig_feat}"] = res_df.iloc[row_idx][rust_feat]
            
            if self.include_last:
                stats[f"{col_name}_last"] = data[-1, i]

        return stats

# Alias for backward compatibility if needed, but we're switching
ExpandingFeatureExtractor = FeatureExtractor
