import numpy as np
from scipy.spatial.distance import cosine

def extract_cosine_distances(window, axes=['ac_x', 'ac_y', 'ac_z', 'g_x', 'g_y', 'g_z']):
    """
    Wyciąga odległości cosinusowe między parami osi czujników (ac_* i g_*) z ramki czasowej.

    Zwraca:
        dict: cechy odległości
    """
    features = {}

    # Akcelerometr
    features['cos_ac_xy'] = 1 - cosine(window[axes[0]], window[axes[1]])
    features['cos_ac_xz'] = 1 - cosine(window[axes[0]], window[axes[2]])
    features['cos_ac_yz'] = 1 - cosine(window[axes[1]], window[axes[2]])

    # Żyroskop
    features['cos_g_xy'] = 1 - cosine(window[axes[3]], window[axes[4]])
    features['cos_g_xz'] = 1 - cosine(window[axes[3]], window[axes[5]])
    features['cos_g_yz'] = 1 - cosine(window[axes[4]], window[axes[5]])

    return features
