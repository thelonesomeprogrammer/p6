import pyarrow as pa
import numpy as np
from ._p6 import ExpandingExtractor as _ExpandingExtractor
from . import utils

class ExpandingFeatureExtractor:
    def __init__(self, features=None, columns=None):
        """
        features: List of feature names (e.g., ["mean", "max_value", "std_dev"])
        columns: List of column names to expect in the input batches
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
        
        # Map some common names to Rust internal names if necessary
        # Rust names: mean, std_dev, max_value, min_value, median, slope, etc.
        name_mapping = {
            "std": "std_dev",
            "max": "max_value",
            "min": "min_value",
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
        self.extractor = _ExpandingExtractor(rust_features, self.n_cols)
        self.rust_features = rust_features

    def reset(self):
        """Reset the internal Rust extractor state."""
        self.extractor = _ExpandingExtractor(self.rust_features, self.n_cols)

    def update(self, df):
        """
        Update the extractor with new data from a pandas DataFrame.
        Returns a dictionary containing the extracted features for each column.
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
        
        stats = {}
        for i, col_name in enumerate(self.columns):
            for rust_feat in self.rust_features:
                orig_feat = self.rust_to_original[rust_feat]
                stats[f"{col_name}_{orig_feat}"] = res_df.iloc[i][rust_feat]
            
            if self.include_last:
                stats[f"{col_name}_last"] = data[-1, i]

        return stats
