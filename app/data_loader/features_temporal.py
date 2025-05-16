import numpy as np
from scipy.signal import find_peaks

def autocorr(x, lag=1):
    """Korelacja sygnału z samym sobą przesuniętym o `lag` próbek"""
    if len(x) <= lag:
        return 0
    return np.corrcoef(x[:-lag], x[lag:])[0, 1]

def extract_temporal_features(window, axes = ['ac_x', 'ac_y', 'ac_z']):
    """
    Wyciąga cechy czasowe z akcelerometru z pojedynczego okna czasowego.

    Parametry:
        window (pd.DataFrame): Ramka z kolumnami 'ac_x', 'ac_y', 'ac_z'

    Zwraca:
        dict: cechy czasowe
    """
    features = {}
    

    for axis in axes:
        signal = window[axis].values

        # 1. Zero crossings
        zero_crossings = ((signal[:-1] * signal[1:]) < 0).sum()
        features[f'{axis}_zero_crossings'] = zero_crossings

        # 2. Mean crossings
        mean_val = np.mean(signal)
        mean_crossings = ((signal[:-1] - mean_val) * (signal[1:] - mean_val) < 0).sum()
        features[f'{axis}_mean_crossings'] = mean_crossings

        # 3. Peaks
        peaks, _ = find_peaks(signal)
        features[f'{axis}_num_peaks'] = len(peaks)

        # 4. Range
        features[f'{axis}_range'] = np.max(signal) - np.min(signal)

        # 5. Energy (z normalizacją)
        features[f'{axis}_energy'] = np.sum(signal ** 2) / len(signal)

        # 6. Autokorelacja (lag 1 i 5)
        features[f'{axis}_autocorr_lag1'] = autocorr(signal, lag=1)
        features[f'{axis}_autocorr_lag5'] = autocorr(signal, lag=5)

    # 7. SMA – Signal Magnitude Area (ze wszystkich osi)
    N = len(window)
    sma = (np.sum(np.abs(window[axes[0]])) +
           np.sum(np.abs(window[axes[1]])) +
           np.sum(np.abs(window[axes[2]]))) / N
    features['sma'] = sma

    return features
