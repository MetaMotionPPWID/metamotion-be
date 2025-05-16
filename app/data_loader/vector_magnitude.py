import numpy as np

def calculate_accelerometer_magnitude(window, axes = ['ac_x', 'ac_y', 'ac_z']):
    """
    Oblicza średnią wartość wektora wielkości (sqrt(x^2 + y^2 + z^2)) dla akcelerometru w oknie czasowym

    Argumenty:
        window: DataFrame reprezentujący pojedyncze okno czasowe

    Zwraca:
        float: Średnia wartość wektora wielkości dla akcelerometru
    """
    
    for axis in axes:
        if axis not in window.columns:
            raise ValueError(f"Kolumna '{axis}' nie została znaleziona w DataFrame.")

    vector_magnitude = np.sqrt(window[axes[0]]**2 + window[axes[1]]**2 + window[axes[2]]**2)
    return vector_magnitude.mean()

def calculate_gyroscope_magnitude(window, axes = ['g_x', 'g_y', 'g_z']):
    """
    Oblicza średnią wartość wektora wielkości (sqrt(x^2 + y^2 + z^2)) dla żyroskopu w oknie czasowym

    Argumenty:
        window: DataFrame reprezentujący pojedyncze okno czasowe

    Zwraca:
        float: Średnia wartość wektora wielkości dla żyroskopu
    """
    
    for axis in axes:
        if axis not in window.columns:
            raise ValueError(f"Kolumna '{axis}' nie została znaleziona w DataFrame.")

    vector_magnitude = np.sqrt(window[axes[0]]**2 + window[axes[1]]**2 + window[axes[2]]**2)
    return vector_magnitude.mean()