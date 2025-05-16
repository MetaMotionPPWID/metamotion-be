import numpy as np

def extract_acc_features(window, axes=['ac_x', 'ac_y', 'ac_z']):
    """
    Wyciąga cechy statystyczne z kolumn ac_x, ac_y, ac_z z ramki `window`.

    Parametry:
        window (pd.DataFrame): Dane z jednego okna czasowego, z kolumnami 'ac_x', 'ac_y', 'ac_z'
        axes (list): Lista osi, z których mają być wyciągnięte cechy
        
    Zwraca:
        dict: cechy statystyczne
    """
    features = {}


    for axis in axes:
        data = window[axis].values

        features[f'{axis}_mean'] = np.mean(data)
        features[f'{axis}_std'] = np.std(data)
        features[f'{axis}_min'] = np.min(data)
        features[f'{axis}_max'] = np.max(data)
        features[f'{axis}_rms'] = np.sqrt(np.mean(data ** 2))
        features[f'{axis}_abs_sum'] = np.sum(np.abs(data))
        features[f'{axis}_energy'] = np.sum(data ** 2)

        # Jerk – tempo zmian
        jerk = np.diff(data)
        features[f'{axis}_jerk_mean'] = np.mean(np.abs(jerk))
        features[f'{axis}_jerk_std'] = np.std(jerk)
        features[f'{axis}_jerk_max'] = np.max(np.abs(jerk))

    return features
