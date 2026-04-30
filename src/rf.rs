use crate::sliding::SlidingExtractor;
use crate::types::Feature;
use arrow::array::{Float32Array, RecordBatch};
use arrow::pyarrow::PyArrowType;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[derive(Debug, Clone)]
pub struct DecisionTree {
    pub children_left: Vec<i32>,
    pub children_right: Vec<i32>,
    pub feature: Vec<i32>,
    pub threshold: Vec<f64>,
    pub value: Vec<f64>,
}

impl DecisionTree {
    pub fn predict(&self, features: &[f32]) -> f64 {
        let mut node_idx = 0usize;
        while self.children_left[node_idx] != -1 {
            let feat_idx = self.feature[node_idx] as usize;
            if (features[feat_idx] as f64) <= self.threshold[node_idx] {
                node_idx = self.children_left[node_idx] as usize;
            } else {
                node_idx = self.children_right[node_idx] as usize;
            }
        }
        self.value[node_idx]
    }
}

#[derive(Debug, Clone)]
pub struct RandomForest {
    pub trees: Vec<DecisionTree>,
}

impl RandomForest {
    pub fn predict(&self, features: &[f32]) -> f64 {
        let mut sum = 0.0;
        for tree in &self.trees {
            sum += tree.predict(features);
        }
        sum / (self.trees.len() as f64)
    }
}

#[pyclass]
pub struct RFPredictor {
    extractor: SlidingExtractor,
    forest: RandomForest,
    scaler_mean: Vec<f32>,
    scaler_scale: Vec<f32>,
    feature_mapping: Vec<(usize, usize)>,
    n_features: usize,
    input_columns: Vec<String>,
    window_size: usize,
}

#[pymethods]
impl RFPredictor {
    #[new]
    #[pyo3(signature = (model_path, window_size=200, sub_model_key=None, input_columns=None))]
    pub fn new(
        model_path: String,
        window_size: usize,
        sub_model_key: Option<String>,
        input_columns: Option<Vec<String>>,
    ) -> PyResult<Self> {
        Python::with_gil(|py| {
            let joblib = py.import("joblib")?;
            let loaded = joblib.call_method1("load", (model_path,))?;

            let (model, scaler, feature_names_list) = if loaded.is_instance_of::<PyDict>() {
                let dict = loaded.downcast::<PyDict>()?;
                if dict.contains("scaler")? {
                    let key = sub_model_key.ok_or_else(|| {
                        PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "sub_model_key is required for dictionary models",
                        )
                    })?;
                    let m = dict.get_item(key)?.ok_or_else(|| {
                        PyErr::new::<pyo3::exceptions::PyKeyError, _>("sub_model_key not found")
                    })?;
                    let s = dict.get_item("scaler")?.ok_or_else(|| {
                        PyErr::new::<pyo3::exceptions::PyKeyError, _>("scaler not found")
                    })?;
                    let f = dict.get_item("features")?.ok_or_else(|| {
                        PyErr::new::<pyo3::exceptions::PyKeyError, _>("features not found")
                    })?;
                    (m, s, f)
                } else if dict.contains("model")? {
                    let m = dict.get_item("model")?.unwrap();
                    let s = dict.get_item("scaler")?.unwrap();
                    let f = dict.get_item("features")?.unwrap();
                    (m, s, f)
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "Unknown dictionary model format",
                    ));
                }
            } else {
                return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                    "Expected dictionary model (joblib)",
                ));
            };

            let feature_names = feature_names_list.downcast::<PyList>()?;

            // Extract trees
            let estimators_bound = model.getattr("estimators_")?;
            let estimators = estimators_bound.downcast::<PyList>()?;
            let mut trees = Vec::with_capacity(estimators.len());
            for est in estimators.iter() {
                let tree = est.getattr("tree_")?;
                let children_left: Vec<i32> = tree.getattr("children_left")?.extract()?;
                let children_right: Vec<i32> = tree.getattr("children_right")?.extract()?;
                let feature: Vec<i32> = tree.getattr("feature")?.extract()?;
                let threshold: Vec<f64> = tree.getattr("threshold")?.extract()?;
                let value: Vec<f64> = tree.getattr("value")?.call_method0("flatten")?.extract()?;

                trees.push(DecisionTree {
                    children_left,
                    children_right,
                    feature,
                    threshold,
                    value,
                });
            }

            let scaler_mean: Vec<f32> = scaler.getattr("mean_")?.extract()?;
            let scaler_scale: Vec<f32> = scaler.getattr("scale_")?.extract()?;

            let cols = input_columns.unwrap_or_else(|| {
                vec![
                    "Torque (Nm)".to_string(),
                    "Position (rad)".to_string(),
                    "Velocity (rad/s)".to_string(),
                ]
            });

            let mut unique_features = std::collections::BTreeSet::new();

            for fname_obj in feature_names.iter() {
                let fname: String = fname_obj.extract()?;
                let mut found = false;
                
                // 1. Try exact match with column names
                for (col_idx, col_name) in cols.iter().enumerate() {
                    if fname.starts_with(col_name) && fname.len() > col_name.len() {
                        let feat_name = &fname[col_name.len() + 1..];
                        let feature = Feature::from(feat_name.to_string());
                        let rust_feat_name = feature.name();
                        unique_features.insert(rust_feat_name);
                        found = true;
                        break;
                    }
                }
                
                // 2. Try normalized match (e.g. 'torque_Max' with 'Torque (Nm)')
                if !found {
                    let fname_lower = fname.to_lowercase();
                    for (col_idx, col_name) in cols.iter().enumerate() {
                        let col_norm = col_name.to_lowercase().replace(" (nm)", "").replace(" (v)", "");
                        if fname_lower.starts_with(&col_norm) && fname.len() > col_norm.len() {
                             // Try to find where the feature name starts (usually after _)
                             if let Some(pos) = fname.find('_') {
                                 let feat_part = &fname[pos+1..];
                                 let feature = Feature::from(feat_part.to_string());
                                 let rust_feat_name = feature.name();
                                 unique_features.insert(rust_feat_name);
                                 found = true;
                                 break;
                             }
                        }
                    }
                }
                
                // 3. Fallback: if no column name found, but it has a prefix we recognize
                if !found {
                    let feature = Feature::from(fname.clone());
                    let rust_feat_name = feature.name();
                    // We need to decide which column this belongs to. 
                    // If we only have one column, it's easy.
                    if cols.len() == 1 {
                        unique_features.insert(rust_feat_name);
                        found = true;
                    }
                }

                if !found {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Could not map feature name: {}",
                        fname
                    )));
                }
            }

            let sorted_unique_features: Vec<String> = unique_features.into_iter().collect();
            let extractor =
                SlidingExtractor::new(sorted_unique_features.clone(), cols.len(), window_size, 1);

            let mut feature_mapping = Vec::new();
            for fname_obj in feature_names.iter() {
                let fname: String = fname_obj.extract()?;
                let mut found = false;
                
                // 1. Exact match
                for (col_idx, col_name) in cols.iter().enumerate() {
                    if fname.starts_with(col_name) && fname.len() > col_name.len() {
                        let feat_name = &fname[col_name.len() + 1..];
                        let feature = Feature::from(feat_name.to_string());
                        let rust_feat_name = feature.name();
                        let feat_idx = sorted_unique_features.iter().position(|f| f == &rust_feat_name).unwrap();
                        feature_mapping.push((col_idx, feat_idx));
                        found = true;
                        break;
                    }
                }
                
                // 2. Normalized match
                if !found {
                    let fname_lower = fname.to_lowercase();
                    for (col_idx, col_name) in cols.iter().enumerate() {
                        let col_norm = col_name.to_lowercase().replace(" (nm)", "").replace(" (v)", "");
                        if fname_lower.starts_with(&col_norm) && fname.len() > col_norm.len() {
                             if let Some(pos) = fname.find('_') {
                                 let feat_part = &fname[pos+1..];
                                 let feature = Feature::from(feat_part.to_string());
                                 let rust_feat_name = feature.name();
                                 let feat_idx = sorted_unique_features.iter().position(|f| f == &rust_feat_name).unwrap();
                                 feature_mapping.push((col_idx, feat_idx));
                                 found = true;
                                 break;
                             }
                        }
                    }
                }

                // 3. Fallback
                if !found && cols.len() == 1 {
                    let feature = Feature::from(fname.clone());
                    let rust_feat_name = feature.name();
                    let feat_idx = sorted_unique_features.iter().position(|f| f == &rust_feat_name).unwrap();
                    feature_mapping.push((0, feat_idx));
                    found = true;
                }
            }

            Ok(Self {
                extractor,
                forest: RandomForest { trees },
                scaler_mean,
                scaler_scale,
                feature_mapping,
                n_features: feature_names.len(),
                input_columns: cols,
                window_size,
            })
        })
    }

    pub fn predict(&mut self, batch: PyArrowType<RecordBatch>) -> PyResult<Option<f64>> {
        let res_batch_py = self.extractor.update(batch)?;
        let res_batch = res_batch_py.0;

        if res_batch.num_rows() == 0 {
            return Ok(None);
        }

        // SlidingExtractor returns (n_rows * n_cols) rows.
        // Stacked by column: [col0_row0, col0_row1, ..., col1_row0, col1_row1, ...]
        // RFPredictor usually expects one result per window.
        // For simplicity, we assume one window completed or we take the last one.
        let n_results = res_batch.num_rows() / self.input_columns.len();
        if n_results == 0 {
            return Ok(None);
        }

        // Use the latest window result
        let mut feat_vec = vec![0.0f32; self.n_features];
        for (i, &(col_idx, feat_idx)) in self.feature_mapping.iter().enumerate() {
            // feat_idx is the index into the RecordBatch columns
            let col_array = res_batch
                .column(feat_idx)
                .as_any()
                .downcast_ref::<Float32Array>()
                .unwrap();
            // Index for col_idx and last result: (col_idx + 1) * n_results - 1
            let row_idx = (col_idx + 1) * n_results - 1;
            let val = col_array.value(row_idx);
            feat_vec[i] = (val - self.scaler_mean[i]) / self.scaler_scale[i];
        }

        let prediction = self.forest.predict(&feat_vec);
        Ok(Some(prediction))
    }

    pub fn reset(&mut self) {
        let feature_strs: Vec<String> = self.extractor.features.iter().map(|f| f.name()).collect();
        self.extractor =
            SlidingExtractor::new(feature_strs, self.input_columns.len(), self.window_size, 1);
    }
}
