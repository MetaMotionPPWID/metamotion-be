import numpy as np
import pandas as pd

def calculate_binned_distribution(window, column, bins=10, range_min=None, range_max=None):
    """
    Oblicza rozkład wartości w określonej liczbie przedziałów (bins) dla danej kolumny w oknie czasowym

    Argumenty:
        window: DataFrame reprezentujący pojedyncze okno czasowe
        column: Nazwa kolumny, dla której ma zostać obliczony rozkład
        bins: Liczba przedziałów 
        range_min: Minimalna wartość zakresu (domyślnie None, co oznacza automatyczne wykrycie)
        range_max: Maksymalna wartość zakresu (domyślnie None, co oznacza automatyczne wykrycie)

    """
    if column not in window.columns:
        raise ValueError(f"Kolumna '{column}' nie została znaleziona w DataFrame.")

    if range_min is None:
        range_min = window[column].min()
    if range_max is None:
        range_max = window[column].max()

    histogram, bin_edges = np.histogram(window[column], bins=bins, range=(range_min, range_max))

    return histogram

def calculate_binned_distribution_multi_axis(window, axes, bins=10, range_min=None, range_max=None):
    """
    Oblicza rozkład wartości w określonej liczbie przedziałów dla wielu osi

    Argumenty:
        window: DataFrame reprezentujący pojedyncze okno czasowe
        axes: Lista nazw kolumn dla osi (np. ['ac_x', 'ac_y', 'ac_z'])
        bins: Liczba przedziałów 
        range_min: Minimalna wartość zakresu
        range_max: Maksymalna wartość zakresu

    """
    distributions = {}
    for axis in axes:
        distributions[f"binned_{axis}"] = calculate_binned_distribution(window, column=axis, bins=bins, range_min=range_min, range_max=range_max)
    return distributions