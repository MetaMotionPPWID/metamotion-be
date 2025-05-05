from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from permissions import user_permission
from utils.handle_errors import handle_db_errors, handle_validation_errors
from model.sensor import Sensor

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
