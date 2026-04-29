import os
import numpy as np
import pyarrow as pa
from ._p6 import RFPredictor as _RFPredictor
from .utils import normalize_columns, INPUT_FEATURES

class FastRFPredictor:
    def __init__(self, model_path="regressors_slide.joblib", sub_model_key="rf", input_columns=None):
        """
        High-performance Random Forest predictor with Rust-based extraction and inference.
        
        model_path: Path to the .joblib or .pkl file.
        sub_model_key: The key in the joblib dictionary for the model (e.g., 'rf' or 'xgb').
        input_columns: List of columns to use from the input DataFrame. Defaults to utils.INPUT_FEATURES.
        """
        if input_columns is None:
            input_columns = INPUT_FEATURES
            
        if not os.path.exists(model_path):
            # Try to find it in the same directory as this file
            local_path = os.path.join(os.path.dirname(__file__), model_path)
            if os.path.exists(local_path):
                model_path = local_path
            else:
                # Check usb subdir relative to this file
                usb_path = os.path.join(os.path.dirname(__file__), "usb", model_path)
                if os.path.exists(usb_path):
                    model_path = usb_path
                else:
                    raise FileNotFoundError(f"Model file {model_path} not found.")

        self.input_columns = input_columns
        self.predictor = _RFPredictor(model_path, sub_model_key=sub_model_key, input_columns=self.input_columns)

    def reset(self):
        """Reset the internal feature extractor state."""
        self.predictor.reset()

    def predict(self, df_window):
        """
        Perform prediction on a window of data.
        df_window: pandas DataFrame containing the newest data.
        Returns: A dictionary with 'remaining_angle'.
        """
        if len(df_window) < 2:
            return None
            
        # Ensure correct columns and types
        mapped_df = normalize_columns(df_window)
        
        # Check if all required columns are present
        if not all(col in mapped_df.columns for col in self.input_columns):
            return None
            
        data = mapped_df[self.input_columns].values.astype(np.float32)
        
        # Convert to Arrow RecordBatch
        # Note: We pass the entire window, the internal Rust extractor handles 
        # the "expanding" state and only processes new rows.
        arrays = [pa.array(data[:, i]) for i in range(len(self.input_columns))]
        batch = pa.RecordBatch.from_arrays(arrays, names=self.input_columns)
        
        prediction = self.predictor.predict(batch)
        if prediction is None:
            return None
            
        return {
            "remaining_angle": float(prediction)
        }
