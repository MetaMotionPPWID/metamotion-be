from scipy.signal import find_peaks
import numpy as np


def extract_peak_features(window_df, sampling_rate, axes=['g_x', 'g_y', 'g_z', 'ac_x', 'ac_y', 'ac_z']):
    features = {}

    for col in axes:
        signal = window_df[col].values
        peaks, _ = find_peaks(signal)

        if len(peaks) > 1:
            peak_times = peaks / sampling_rate
            time_diff = np.diff(peak_times)
            avg_time_between_peaks = np.mean(time_diff)
            std_time_between_peaks = np.std(time_diff)
        else:
            avg_time_between_peaks = 0
            std_time_between_peaks = 0

        features[f'peak_avg_time_diff_{col}'] = avg_time_between_peaks
        features[f'peak_std_time_diff_{col}'] = std_time_between_peaks
        features[f'peak_count_{col}'] = len(peaks)

    return features
