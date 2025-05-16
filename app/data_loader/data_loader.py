import pandas as pd
from tqdm import tqdm


class TimeWindowSegmenter:
    def __init__(
        self,
        df=None,
        df_path=None,
        window_size=10,
        source_sampling_rate=20,
        step_size=10,
        time_column="Timestamp",
        id_column="Subject-id",
        activity_column="Activity Label",
        clean_columns=True,
        fix_timestamps=True,
        acc_columns=("ac_x", "ac_y", "ac_z"),
        gyr_columns=("g_x", "g_y", "g_z"),
    ):
        self.window_size = window_size  # in seconds
        self.step_size = step_size  # in seconds
        self.time_column = time_column
        self.id_column = id_column
        self.activity_column = activity_column
        self.acc_columns = acc_columns
        self.gyr_columns = gyr_columns
        self.sampling_rate = source_sampling_rate

        if df is not None:
            self.df = df
        elif df_path is not None:
            self.df = pd.read_parquet(df_path, engine="pyarrow")
        else:
            raise ValueError("Either df or df_path must be provided")

        if clean_columns:
            self._clean_columns()

        if fix_timestamps:
            self._fix_timestamps()

    def _clean_columns(self):
        for col in list(self.acc_columns) + list(self.gyr_columns):
            if col in self.df.columns:
                self.df[col] = (
                    self.df[col]
                    .astype(str)
                    .str.replace(";", "", regex=False)
                    .str.extract(r"([-+]?\d*\.\d+|\d+)")[0]  # tylko liczba
                    .astype(float)
                )

    def _fix_unix_timestamp(self, timestamp_series):
        ts_str = timestamp_series.astype(str).str.replace(r"\D", "", regex=True)

        def safe_convert(ts):
            try:
                ts_int = int(str(ts)[:13])
                return pd.to_datetime(ts_int, unit="ms")
            except Exception:
                return pd.NaT

        return ts_str.apply(safe_convert)

    def _fix_timestamps(self):
        print("Fixing timestamps...")
        self.df[self.time_column] = self._fix_unix_timestamp(self.df[self.time_column])
        self.df.sort_values(
            by=[self.id_column, self.activity_column, self.time_column], inplace=True
        )
        print("Done fixing timestamps.")

    def resample_to(self, target_rate_hz):
        """
        Resamples the data to a new frequency (Hz) using time-based resampling.
        Handles missing time intervals by filling gaps before resampling.
        """
        grouped = self.df.groupby([self.id_column, self.activity_column])
        period_ms = int(1000 / self.sampling_rate)
        target_period_ms = int(1000 / target_rate_hz)
        resampled_df = pd.DataFrame()

        for (pid, act), group in tqdm(grouped, desc="Resampling"):
            group[self.id_column] = pid
            group[self.activity_column] = act
            group[self.time_column] = pd.to_datetime(group[self.time_column], unit="ms")
            group[self.time_column] = group[self.time_column].dt.round(f"{period_ms}ms")
            group = group.set_index(self.time_column).sort_index()
            group = group[~group.index.duplicated(keep="first")]
            ideal_index = pd.date_range(
                start=group.index.min(), end=group.index.max(), freq=f"{period_ms}ms"
            )
            group = group.reindex(ideal_index)
            numeric_cols = group.select_dtypes(include="number").columns
            const_cols = [self.id_column, self.activity_column]
            group[numeric_cols] = group[numeric_cols].interpolate(method="linear")
            group[const_cols] = group[const_cols].ffill().bfill()
            group = group.reset_index().rename(columns={"index": self.time_column})
            group[self.time_column] = pd.to_datetime(group[self.time_column], unit="ms")
            group = group.set_index(self.time_column)
            numeric_cols = group.select_dtypes(include="number").columns
            group_resampled = (
                group[numeric_cols].resample(f"{target_period_ms}ms").mean()
            )
            for col in const_cols:
                group_resampled[col] = (
                    group[col].resample(f"{target_period_ms}ms").ffill()
                )
            group_resampled = group_resampled.reset_index()
            resampled_df = pd.concat([resampled_df, group_resampled])

        self.df = resampled_df
        self.df = self.df.reset_index(drop=True)

    def segment(self):
        """
        usage:
        ```python
            for segment in TimeWindowSegmenter.segment():
                print(segment)
        ```

        Yields:
            _type_: dataframe - window of data by time
        """
        grouped = self.df.groupby([self.id_column, self.activity_column])

        for (_, _), group in tqdm(grouped, total=len(grouped), desc="Segmenting"):
            for window in group.rolling(
                window=self.window_size * self.sampling_rate,
                step=self.step_size * self.sampling_rate,
                on=self.time_column,
            ):
                if window.shape[0] != self.window_size * self.sampling_rate:
                    continue
                yield window


def check_time_continuity(
    df,
    sampling_rate_hz,
    allowed_deviation_ms=5,
    timestamp_col="timestamp",
    silent=False,
):
    """
    Sprawdza czy próbki są równomiernie rozstawione zgodnie z oczekiwanym sampling rate.

    Args:
        df (pd.DataFrame): fragment danych (np. z segmentera)
        sampling_rate_hz (int or float): spodziewana częstotliwość próbkowania (np. 25)
        allowed_deviation_ms (int): dopuszczalna odchyłka w milisekundach (np. 5)
        timestamp_col (str): nazwa kolumny z czasem

    Returns:
        bool: True jeśli odstępy są spójne z sampling rate, False jeśli wykryto odstępstwa
    """
    if df.empty or len(df) < 2:
        print("Dane są zbyt krótkie do sprawdzenia.")
        return False

    # Upewniamy się, że kolumna to datetime
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df = df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], unit="ms")

    expected_delta = 1000 / sampling_rate_hz  # w ms
    deltas = df[timestamp_col].diff().dropna().dt.total_seconds() * 1000  # w ms

    # Sprawdź, które odstępy są poza tolerancją
    out_of_range = deltas[
        (deltas < (expected_delta - allowed_deviation_ms))
        | (deltas > (expected_delta + allowed_deviation_ms))
    ]

    if not out_of_range.empty:
        if silent:
            print(
                f"⚠️ Wykryto {len(out_of_range)} nieciągłości w czasie (oczekiwano ~{expected_delta:.2f} ms):"
            )
            print(out_of_range.head(5))  # pokaż kilka
        return False

    return True
