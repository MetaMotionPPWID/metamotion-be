import numpy as np
from scipy.signal import welch
from scipy.fft import fft
import librosa


def dominant_frequency(signal, fs=20):
    """
    Dominująca częstotliwość to ta składowa częstotliwościowa sygnału, 
    która posiada największą moc (czyli największą amplitudę w widmie mocy). 
    Jest to częstotliwość, która dominuje energetycznie w analizowanym odcinku czasu.
    """
    freqs, psd = welch(signal, fs, nperseg=len(signal))
    dom_freq = freqs[np.argmax(psd)]
    return dom_freq


def spectral_entropy(signal, fs=20):
    """
     Entropia widmowa to miara nieuporządkowania lub losowości rozkładu widmowego sygnału. 
     Bazuje na teorii informacji (entropii Shannona) i opisuje, jak równomiernie rozłożona 
     jest energia sygnału w domenie częstotliwości.

     - Niska entropia oznacza, że energia jest skoncentrowana wokół kilku częstotliwości — sygnał jest bardziej "uporządkowany".
     - Wysoka entropia sugeruje rozproszenie energii po wielu częstotliwościach — sygnał jest bardziej "chaotyczny"
    """
    _, psd = welch(signal, fs, nperseg=len(signal))
    psd_norm = psd / np.sum(psd)  # normalizacja
    entropy = -np.sum(psd_norm * np.log2(psd_norm + 1e-12))  # dodajemy epsilon żeby uniknąć log(0)
    entropy /= np.log2(len(psd_norm))  # normalizacja do [0,1]
    return entropy


def spectral_energy(signal):
    """
    Energia widmowa to całkowita suma energii zawarta w widmie sygnału. 
    Można ją rozumieć jako "siłę" sygnału rozłożoną w dziedzinie częstotliwości.
    
    - Pomaga ocenić ogólną intensywność sygnału — im większa energia, tym silniejszy 
    jest sygnał w danym zakresie czasu.
    """
    spectrum = np.abs(fft(signal))**2
    energy = np.sum(spectrum) / len(spectrum) # normalizujemy do długości sygnału
    return energy


def spectral_centroid(signal, fs=20):
    """
    Centroid widmowy to "środek ciężkości" widma sygnału — informuje, gdzie 
    w domenie częstotliwości skoncentrowana jest energia.

    - Niski centroid: energia skupiona w niskich częstotliwościach (np. wolne ruchy).
    - Wysoki centroid: energia przesunięta w wyższe pasma.
    """
    freqs, psd = welch(signal, fs, nperseg=len(signal))
    psd_norm = psd / np.sum(psd)
    centroid = np.sum(freqs * psd_norm)
    return centroid


def spectral_bandwidth(signal, fs=20):
    """
    Szerokość pasma — odchylenie standardowe widma względem środka ciężkości (centroidu).

    - Małe pasmo sugeruje, że sygnał zawiera głównie wąski zakres częstotliwości.
    - Duże pasmo oznacza obecność wielu różnych składowych częstotliwościowych — np. złożone sygnały biologiczne.
    """
    freqs, psd = welch(signal, fs, nperseg=len(signal))
    psd_norm = psd / np.sum(psd)
    centroid = np.sum(freqs * psd_norm)
    bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * psd_norm))
    return bandwidth


def spectral_flatness(signal, fs=20):
    """
    Spłaszczenie widmowe to miara „szumowatości” sygnału. 
    - Wartość bliska 1: rozłożona energia, przypomina szum.
    - Wartość bliska 0: jedna dominująca częstotliwość (ton).
    """
    _, psd = welch(signal, fs, nperseg=len(signal))
    geometric_mean = np.exp(np.mean(np.log(psd + 1e-12)))  # epsilon zapobiega log(0)
    arithmetic_mean = np.mean(psd)
    flatness = geometric_mean / (arithmetic_mean + 1e-12)
    return flatness


def spectral_slope(signal, fs=20):
    """
    Nachylenie widmowe to kierunek trendu widma — informuje, czy amplitudy 
    rosną czy maleją wraz ze wzrostem częstotliwości.
    
    - Dodatnie: więcej energii w wyższych częstotliwościach.
    - Ujemne: dominacja niższych pasm.
    """
    freqs, psd = welch(signal, fs, nperseg=len(signal))
    X = freqs
    Y = 10 * np.log10(psd + 1e-12)
    slope = np.polyfit(X, Y, 1)[0]  # nachylenie regresji liniowej
    return slope


def spectral_rolloff(signal, fs=20, roll_percent=0.85):
    """
    Częstotliwość roll-off to taka, poniżej której znajduje się X% całkowitej energii.
    
    - Pomaga określić „górne pasmo” sygnału.
    - Typowe wartości X: 0.85 lub 0.95
    """
    freqs, psd = welch(signal, fs, nperseg=len(signal))
    cumulative_energy = np.cumsum(psd)
    threshold = roll_percent * cumulative_energy[-1]
    rolloff_idx = np.where(cumulative_energy >= threshold)[0][0]
    rolloff_freq = freqs[rolloff_idx]
    return rolloff_freq


def band_energy_ratio(signal, fs=20, low_band=(0.0, 10.0), high_band=(10.0, 20.0)):
    """
    Stosunek energii w dwóch zakresach częstotliwości — np. [0–10 Hz] vs. [10–20 Hz].
    - Przydatne do odróżniania typów ruchu (np. chód vs. bieganie).
    """
    freqs, psd = welch(signal, fs, nperseg=len(signal))

    low_mask = (freqs >= low_band[0]) & (freqs < low_band[1])
    high_mask = (freqs >= high_band[0]) & (freqs < high_band[1])

    low_energy = np.sum(psd[low_mask])
    high_energy = np.sum(psd[high_mask])
    
    ratio = low_energy / (high_energy + 1e-12)
    return ratio


def mfcc_features(signal, fs=50, n_mfcc=13):
    """
    Oblicza współczynniki MFCC dla danego sygnału. 
    UWAGA: MFCC ma sens tylko jak będziemy mieć większe FS niż 50Hz.

    Parametry:
    - signal: 1D array – sygnał wejściowy z jednej osi czujnika
    - fs: int – częstotliwość próbkowania (Hz), domyślnie 100 Hz
    - n_mfcc: int – liczba współczynników MFCC do zwrócenia

    Zwraca:
    - wektor cech: średnie wartości każdego z n_mfcc współczynników
    """
    mfcc = librosa.feature.mfcc(y=signal.astype(float), sr=fs, n_mfcc=n_mfcc)
    mfcc_mean = np.mean(mfcc, axis=1)  # uśredniamy po czasie
    return mfcc_mean