import numpy as np

def lttb_indices(data_x, data_y, threshold):
    """
    Calculates the indices of points to keep using LTTB.
    data_x: 1D array-like
    data_y: 1D array-like
    threshold: number of points to keep
    Returns: list of indices
    """
    n_points = len(data_x)
    if threshold >= n_points or threshold <= 2:
        return list(range(n_points))

    data_x = np.array(data_x)
    data_y = np.array(data_y)

    n_bins = threshold - 2
    bin_size = (n_points - 2) / n_bins
    
    indices = [0] # Always keep first point
    
    for i in range(n_bins):
        # Calculate range for current bin
        start = int(np.floor((i) * bin_size) + 1)
        end = int(np.floor((i + 1) * bin_size) + 1)
        
        # Calculate range for next bin to calculate average point
        next_start = int(np.floor((i + 1) * bin_size) + 1)
        next_end = int(np.floor((i + 2) * bin_size) + 1)
        
        if next_end > n_points:
            next_end = n_points
            
        avg_x_next = np.mean(data_x[next_start:next_end])
        avg_y_next = np.mean(data_y[next_start:next_end])
        
        a_x = data_x[indices[-1]]
        a_y = data_y[indices[-1]]
        
        # Optimize triangle area calculation
        # Area = 0.5 * |x1(y2-y3) + x2(y3-y1) + x3(y1-y2)|
        term1 = avg_y_next - a_y
        
        bin_x = data_x[start:end]
        bin_y = data_y[start:end]
        
        areas = 0.5 * np.abs(
            a_x * (bin_y - avg_y_next) + 
            bin_x * term1 + 
            avg_x_next * a_y - avg_x_next * bin_y
        )
        
        selected_index = start + np.argmax(areas)
        indices.append(selected_index)
        
    indices.append(n_points - 1) # Always keep last point
    return indices
