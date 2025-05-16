from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.permissions import user_permission
from app.utils.handle_errors import handle_db_errors, handle_validation_errors
from app.model.sensor import Sensor
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

sample_schema_list = sensors_bp.model(
    "SampleList",
    {
        "samples": fields.List(fields.Nested(sample_schema)),
    },
)

prediction_schema = sensors_bp.model(
    "Prediction",
    {
        "timestamp": fields.DateTime(
            required=True, description="The timestamp of the prediction window"
        ),
        "predicted_activity": fields.String(
            required=True, description="The predicted activity label"
        ),
    },
)

prediction_schema_list = sensors_bp.model(
    "PredictionList",
    {
        "predictions": fields.List(fields.Nested(prediction_schema)),
    },
)

time_range_schema = sensors_bp.model(
    "TimeRange",
    {
        "start_time": fields.DateTime(
            required=True, description="Start time in ISO format"
        ),
        "end_time": fields.DateTime(
            required=True, description="End time in ISO format"
        ),
    },
)

sensor_schema_list = sensors_bp.model(
    "SensorList",
    {
        "sensors": fields.List(fields.Nested(sensor_schema)),
    },
)


@sensors_bp.route("/")
class SensorsList(Resource):
    @sensors_bp.marshal_list_with(sensor_schema_list)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def get(self):
        username = get_jwt_identity()
        return {"sensors": Sensor.get_user_sensors(username)}

    @sensors_bp.expect(sensor_schema)
    @sensors_bp.marshal_with(sensor_schema)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def post(self):
        data = sensors_bp.payload
        mac = data["mac"]
        name = data["name"]
        samples = data["samples"]
        username = get_jwt_identity()
        return Sensor.create_sensor(mac, name, username, samples)


@sensors_bp.route("/<string:mac>")
class SensorObject(Resource):
    @sensors_bp.marshal_with(sensor_schema)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def get(self, mac):
        sensor = Sensor.get_sensor_by_mac(mac)
        if not sensor:
            return {"message": "Sensor not found"}, 404
        return sensor


@sensors_bp.route("/<string:mac>/samples")
class SensorSamples(Resource):
    @sensors_bp.marshal_with(sample_schema_list)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def get(self, mac):
        sensor = Sensor.get_sensor_by_mac(mac)
        if not sensor:
            return {"message": "Sensor not found"}, 404
        return {"samples": sensor.samples}

    @sensors_bp.expect(sample_schema_list)
    @sensors_bp.marshal_with(sample_schema_list)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def post(self, mac):
        data = sensors_bp.payload
        samples = data["samples"]
        sensor = Sensor.get_sensor_by_mac(mac)
        if not sensor:
            return {"message": "Sensor not found"}, 404
        saved_samples = Sensor.add_samples(mac, samples).samples
        return {"samples": saved_samples}


@sensors_bp.route("/<string:mac>/samples/prediction")
class SensorSamplesPrediction(Resource):
    @sensors_bp.expect(time_range_schema)
    @sensors_bp.marshal_with(prediction_schema_list)
    @jwt_required()
    @user_permission.require(http_exception=403)
    @handle_validation_errors
    @handle_db_errors
    def post(self, mac):
        data = sensors_bp.payload
        start_time = data["start_time"]
        end_time = data["end_time"]

        sensor = Sensor.get_sensor_by_mac(mac)
        if not sensor:
            return {"message": "Sensor not found"}, 404

        samples = Sensor.get_samples_in_time_range(mac, start_time, end_time)

        df_data = []
        for sample in samples:
            df_data.append(
                {
                    "Timestamp": sample.timestamp,
                    "Subject-id": sensor.mac,
                    "activity_label": sample.label,
                    "acc_x": sample.acceleration[0],
                    "acc_y": sample.acceleration[1],
                    "acc_z": sample.acceleration[2],
                    "gyr_x": sample.gyroscope[0],
                    "gyr_y": sample.gyroscope[1],
                    "gyr_z": sample.gyroscope[2],
                }
            )

        df = pd.DataFrame(df_data)

        df = df.sort_values("Timestamp")

        X = []  # Features
        timestamps = []  # Store timestamps

        results = extract_features_from_window(
            df,
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
        X.append(results)
        timestamps.append(df["Timestamp"].iloc[0])

        X_df = pd.DataFrame(X)

        nan_columns = X_df.columns[X_df.isna().any()].tolist()
        if nan_columns:
            print(f"Columns with NaN values: {nan_columns}")
            X_df = X_df.fillna(0)

        model_path = os.path.join(os.path.dirname(__file__), "..", "model.pkl")
        model = joblib.load(model_path)

        predictions = model.predict(X_df)

        results = []
        for timestamp, prediction in zip(timestamps, predictions):
            results.append(
                {"timestamp": timestamp.isoformat(), "predicted_activity": prediction}
            )

        return {"predictions": results}
