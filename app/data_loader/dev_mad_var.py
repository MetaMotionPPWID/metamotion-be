import pandas as pd
import numpy as np

def calculate_statistics(window, column):
    """
    Oblicza odchylenie standardowe, odchylenie bezwzględne i wariancję dla określonej kolumny w oknie czasowym

    Argumenty:
        window: DataFrame reprezentujący pojedyncze okno czasowe
        column: Nazwa kolumny, dla której mają zostać obliczone statystyki

    """
    if column not in window.columns:
        raise ValueError(f"Column '{column}' not found in the DataFrame.")

    std_dev = window[column].std()
    abs_dev = np.mean(np.abs(window[column] - window[column].mean()))
    variance = window[column].var()

    return std_dev, abs_dev, variance

def calculate_statistics_multi_axis(window, axes):
    """
    Oblicza statystyki (odchylenie standardowe, odchylenie bezwzględne, wariancję) dla wielu osi w oknie czasowym

    Argumenty:
        window: DataFrame reprezentujący pojedyncze okno czasowe
        axes: Lista nazw kolumn dla osi (np. ['ac_x', 'ac_y', 'ac_z'] lub ['g_x', 'g_y', 'g_z'])

    """
    if not axes:
        raise ValueError("The 'axes' parameter must be a non-empty list of column names.")

    stats = {}
    for axis in axes:
        if axis not in window.columns:
            print(f"Warning: Column '{axis}' not found in the DataFrame. Skipping...")
            continue

        stats[f"std_{axis}"], stats[f"abs_{axis}"], stats[f"var_{axis}"] = calculate_statistics(window, axis)
    return stats