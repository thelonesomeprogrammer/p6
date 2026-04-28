#![feature(portable_simd)]
use pyo3::prelude::*;
use numpy::PyReadonlyArray1;

mod types;
mod common;
mod expanding;

#[pyfunction]
fn lttb_indices(data_x: PyReadonlyArray1<f64>, data_y: PyReadonlyArray1<f64>, threshold: usize) -> Vec<usize> {
    let x = data_x.as_array();
    let y = data_y.as_array();
    let n_points = x.len();

    if threshold >= n_points || threshold <= 2 {
        return (0..n_points).collect();
    }

    let n_bins = threshold - 2;
    let bin_size = (n_points - 2) as f64 / n_bins as f64;

    let mut indices = Vec::with_capacity(threshold);
    indices.push(0); // Always keep first point

    for i in 0..n_bins {
        // Calculate range for current bin
        let start = ((i as f64 * bin_size).floor() as usize) + 1;
        let end = (((i + 1) as f64 * bin_size).floor() as usize) + 1;

        // Calculate range for next bin to calculate average point
        let next_start = (((i + 1) as f64 * bin_size).floor() as usize) + 1;
        let mut next_end = (((i + 2) as f64 * bin_size).floor() as usize) + 1;

        if next_end > n_points {
            next_end = n_points;
        }

        let mut avg_x_next = 0.0;
        let mut avg_y_next = 0.0;
        let next_bin_len = (next_end - next_start) as f64;
        
        if next_bin_len > 0.0 {
            for j in next_start..next_end {
                avg_x_next += x[j];
                avg_y_next += y[j];
            }
            avg_x_next /= next_bin_len;
            avg_y_next /= next_bin_len;
        }

        let a_idx = indices[indices.len() - 1];
        let a_x = x[a_idx];
        let a_y = y[a_idx];

        let mut max_area = -1.0;
        let mut selected_index = start;

        for j in start..end {
            // Area = 0.5 * |x1(y2-y3) + x2(y3-y1) + x3(y1-y2)|
            // a: (a_x, a_y), b: (x[j], y[j]), c: (avg_x_next, avg_y_next)
            let area = 0.5 * (a_x * (y[j] - avg_y_next) + x[j] * (avg_y_next - a_y) + avg_x_next * (a_y - y[j])).abs();
            if area > max_area {
                max_area = area;
                selected_index = j;
            }
        }
        indices.push(selected_index);
    }

    indices.push(n_points - 1); // Always keep last point
    indices
}

#[pymodule]
fn _p6(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(lttb_indices, m)?)?;
    m.add_class::<expanding::ExpandingExtractor>()?;
    Ok(())
}
