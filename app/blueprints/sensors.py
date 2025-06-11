from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.permissions import user_permission
from app.utils.handle_errors import handle_db_errors, handle_validation_errors
from app.extension import db
from app.model.sesnor import Sensor, Sample, WindowFeatures
import pandas as pd
import joblib
import os

from app.data_loader import (
    binned_distr,
    dev_mad_var,
    features_accelerometer,
    features_cosine,
    features_freq,
    features_temporal,
    vector_magnitude,
    peak_features,
)


def safe_parse_vector(vector_data, default=[0.0, 0.0, 0.0]):
    """
    Safely parse vector data from request, defaulting to zeros if invalid
    """
    try:
        if not vector_data or not isinstance(vector_data, list):
            return default
        # Ensure we have exactly 3 values, pad with zeros if needed
        while len(vector_data) < 3:
            vector_data.append(0.0)
        # Convert all values to float, use 0.0 for invalid values
        return [float(x) if x is not None else 0.0 for x in vector_data[:3]]
    except Exception:
        return default


def extract_features_from_window(
    window, fs=20, axes=["ac_x", "ac_y", "ac_z", "g_x", "g_y", "g_z"]
):
    features = []
    feature_names = []
    data_freq_dict = {}

    freq_funcs = [
        ("dom_freq", features_freq.dominant_frequency, [fs]),
        ("entropy", features_freq.spectral_entropy, [fs]),
        ("energy", features_freq.spectral_energy, []),
        ("centroid", features_freq.spectral_centroid, [fs]),
        ("bandwidth", features_freq.spectral_bandwidth, [fs]),
        ("flatness", features_freq.spectral_flatness, [fs]),
        ("slope", features_freq.spectral_slope, [fs]),
        ("rolloff", features_freq.spectral_rolloff, [fs]),
        ("band_ratio", features_freq.band_energy_ratio, [fs]),
    ]

    for axis in axes:
        signal = window[axis].astype(float).values
        for fname, func, extra_args in freq_funcs:
            data_freq_dict[f"{axis}_{fname}"] = func(signal, *extra_args)
            # features.append(func(signal, *extra_args))
            # feature_names.append(f"{axis}_{fname}")

    # rozkład wartości względnie dla okna
    data_binned_all_dict = binned_distr.calculate_binned_distribution_multi_axis(
        window=window, bins=10, axes=axes
    )

    data_binned_sep_dict = {
        f"{key}_bin{bin_id}": data
        for key, items in data_binned_all_dict.items()
        for bin_id, data in enumerate(items)
    }

    dev_mad_var_dict = dev_mad_var.calculate_statistics_multi_axis(
        window=window, axes=axes
    )

    acc_features_dict = features_accelerometer.extract_acc_features(
        window=window, axes=axes
    )

    cosine_features_dict = features_cosine.extract_cosine_distances(
        window=window, axes=axes
    )

    temporal_features_dict = features_temporal.extract_temporal_features(
        window=window, axes=axes[3:]
    )

    vector_magnitude_dict = {}
    vector_magnitude_dict["vector_acc_mag"] = (
        vector_magnitude.calculate_accelerometer_magnitude(window=window, axes=axes[:3])
    )
    vector_magnitude_dict["vector_gyr_mag"] = (
        vector_magnitude.calculate_gyroscope_magnitude(window=window, axes=axes[3:])
    )

    peak_features_dict = peak_features.extract_peak_features(
        window_df=window, sampling_rate=fs, axes=axes
    )

    return {
        **data_freq_dict,
        **data_binned_sep_dict,
        **dev_mad_var_dict,
        **acc_features_dict,
        **cosine_features_dict,
        **temporal_features_dict,
        **vector_magnitude_dict,
        **peak_features_dict,
    }


def split_into_windows(df, window_size=250):
    """
    Split DataFrame into windows of specified size.
    Only keeps full windows, discards any partial window at the end.

    Args:
        df (pd.DataFrame): Input DataFrame
        window_size (int): Size of each window in samples

    Returns:
        list: List of DataFrame windows
    """
    n_windows = len(df) // window_size
    windows = []

    for i in range(n_windows):
        start_idx = i * window_size
        end_idx = (i + 1) * window_size
        window = df.iloc[start_idx:end_idx].copy()
        windows.append(window)

    return windows


sensors_bp = Namespace("sensors", description="Sensors related endpoints")

sample_schema = sensors_bp.model(
    "Sample",
    {
        "timestamp": fields.DateTime(
            required=True,
            description="The timestamp of the sample",
        ),
        "label": fields.String(required=True, description="The label of the sample"),
        "watch_on_hand": fields.String(
            required=True, description="The watch on hand of the sample"
        ),
        "acceleration": fields.List(
            fields.Float, required=True, description="The acceleration of the sample"
        ),
        "gyroscope": fields.List(
            fields.Float, required=True, description="The gyroscope of the sample"
        ),
    },
)

sensor_schema = sensors_bp.model(
    "Sensor",
    {
        "mac": fields.String(
            required=True, description="The mac address of the sensor"
        ),
        "name": fields.String(required=True, description="The name of the sensor"),
        "samples": fields.List(
            fields.Nested(sample_schema),
            required=True,
            description="The samples of the sensor",
        ),
    },
)

prediction_result_schema = sensors_bp.model(
    "PredictionResult",
    {
        "timestamp": fields.DateTime(
            required=True,
            description="The timestamp of the window start",
        ),
        "labels": fields.List(
            fields.String,
            required=True,
            description="The predicted activity labels",
        ),
    },
)

prediction_results_schema = sensors_bp.model(
    "PredictionResultList",
    {
        "results": fields.List(
            fields.Nested(prediction_result_schema),
            required=True,
            description="List of prediction results",
        ),
    },
)

# Schema for complete sensor data including database IDs
complete_sample_schema = sensors_bp.model(
    "CompleteSample",
    {
        "id": fields.Integer(required=True, description="Sample database ID"),
        "sensor_id": fields.Integer(required=True, description="Associated sensor ID"),
        "timestamp": fields.DateTime(
            required=True, description="The timestamp of the sample"
        ),
        "label": fields.String(required=True, description="The label of the sample"),
        "watch_on_hand": fields.String(
            required=True, description="The watch on hand of the sample"
        ),
        "acceleration": fields.List(
            fields.Float, required=True, description="The acceleration of the sample"
        ),
        "gyroscope": fields.List(
            fields.Float, required=True, description="The gyroscope of the sample"
        ),
    },
)

complete_sensor_schema = sensors_bp.model(
    "CompleteSensor",
    {
        "id": fields.Integer(required=True, description="Sensor database ID"),
        "mac": fields.String(
            required=True, description="The mac address of the sensor"
        ),
        "name": fields.String(required=True, description="The name of the sensor"),
        "created_at": fields.DateTime(
            required=True, description="Sensor creation timestamp"
        ),
        "updated_at": fields.DateTime(
            required=True, description="Sensor last update timestamp"
        ),
        "samples": fields.List(
            fields.Nested(complete_sample_schema),
            required=True,
            description="The samples of the sensor",
        ),
    },
)

sensors_dump_schema = sensors_bp.model(
    "SensorsDump",
    {
        "sensors": fields.List(
            fields.Nested(complete_sensor_schema),
            required=True,
            description="List of all sensors with their samples",
        ),
        "total_sensors": fields.Integer(
            required=True, description="Total number of sensors"
        ),
        "total_samples": fields.Integer(
            required=True, description="Total number of samples across all sensors"
        ),
    },
)


@sensors_bp.route("/")
class Sensors(Resource):
    @sensors_bp.expect(sensor_schema)
    @sensors_bp.marshal_with(prediction_results_schema)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def post(self):
        data = sensors_bp.payload
        mac = data.get("mac", "unknown")
        name = data.get("name", f"Sensor_{mac}")
        samples = data.get("samples", [])

        df_data = []
        for sample in samples:
            # Safely parse acceleration and gyroscope data
            acceleration = safe_parse_vector(sample.get("acceleration"))
            gyroscope = safe_parse_vector(sample.get("gyroscope"))

            df_data.append(
                {
                    "Timestamp": pd.to_datetime(sample.get("timestamp")),
                    "Subject-id": mac,
                    "activity_label": sample.get("label", "unknown"),
                    "watch_on_hand": sample.get("watch_on_hand", "unknown"),
                    "acc_x": acceleration[0],
                    "acc_y": acceleration[1],
                    "acc_z": acceleration[2],
                    "gyr_x": gyroscope[0],
                    "gyr_y": gyroscope[1],
                    "gyr_z": gyroscope[2],
                }
            )

        if not df_data:
            return {"results": []}

        user_login = get_jwt_identity()

        sensor = Sensor.create_sensor(mac, name, user_login)
        for sample_data in df_data:
            sample = Sample.create_sample(
                timestamp=sample_data["Timestamp"],
                label=sample_data["activity_label"],
                watch_on_hand=sample_data["watch_on_hand"],
                acceleration=[
                    sample_data["acc_x"],
                    sample_data["acc_y"],
                    sample_data["acc_z"],
                ],
                gyroscope=[
                    sample_data["gyr_x"],
                    sample_data["gyr_y"],
                    sample_data["gyr_z"],
                ],
                sensor_id=sensor.id,
            )

        df = pd.DataFrame(df_data)
        df = df.sort_values(by="Timestamp")

        # Split into windows of 250 samples
        windows = split_into_windows(df, window_size=250)

        if len(windows) == 0:
            return {"results": []}

        # Process each window
        data = []
        for window in windows:
            features = extract_features_from_window(
                window,
                fs=25,
                axes=[
                    "acc_x",
                    "acc_y",
                    "acc_z",
                    "gyr_x",
                    "gyr_y",
                    "gyr_z",
                ],
            )
            data.append(features)

        model_path = os.path.join(os.path.dirname(__file__), "..", "model.joblib")
        model = joblib.load(model_path)

        results = []
        for X, index in zip(data, range(len(data))):
            X_df = pd.DataFrame(
                [X]
            )  # Wrap X in a list to create a single-row DataFrame
            result = model.predict(X_df)
            window_start = windows[index]["Timestamp"].iloc[0]

            new_window_features = WindowFeatures(
                sensor_id=sensor.id,
                window_start=window_start,
                features=X,  # JSON-serializable dict
                prediction_label=prediction_label,
            )
            db.session.add(new_window_features)

            results.append(
                {
                    "timestamp": windows[index]["Timestamp"].iloc[0],
                    "labels": list(result),
                }
            )

        return {"results": results}


@sensors_bp.route("/dump")
class SensorsDump(Resource):
    @sensors_bp.marshal_with(sensors_dump_schema)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_db_errors
    def get(self):
        """
        Get all sensors with their complete sample data
        Returns a comprehensive JSON dump of all sensor data in the database
        """
        # Query all sensors with their samples using eager loading
        sensors = Sensor.query.options(db.joinedload(Sensor.samples)).all()

        sensors_data = []
        total_samples = 0

        for sensor in sensors:
            sensor_dict = sensor.to_dict()
            sensors_data.append(sensor_dict)
            total_samples += len(sensor.samples)

        return {
            "total_sensors": len(sensors_data),
            "total_samples": total_samples,
            "sensors": sensors_data,
        }

@sensors_bp.route("/result")
class UserResults(Resource):
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_db_errors
    def get(self):
        """
        Get all prediction results (WindowFeatures) for the currently authenticated user.
        """
        current_user_id = get_jwt_identity()

        results = (
            db.session.query(WindowFeatures)
            .join(Sensor)
            .filter(Sensor.user_id == current_user_id)
            .all()
        )

        results_data = []
        for result in results:
            results_data.append({
                "sensor_id": result.sensor_id,
                "window_start": result.window_start.isoformat(),
                "features": result.features,
                "prediction_label": result.prediction_label
            })

        return {"total_results": len(results_data), "results": results_data}
