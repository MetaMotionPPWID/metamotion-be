import os
from datetime import timedelta
from flask import Flask, current_app, jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_principal import Principal, RoleNeed, Identity, identity_changed
from werkzeug.exceptions import HTTPException
from extension import db, jwt
from model.role import Role
from model.token_white_list import TokenWhiteList

app = Flask(__name__)

hostname = os.getenv("HOST_DB")
port = os.getenv("PGPORT")
database = os.getenv("POSTGRES_DB")
username = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
jwt_secret_key = os.getenv("JWT_SECRET_KEY")

# db = PostgreSQL(hostname=hostname, port=port, database=database, username=username, password=password)

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{username}:{password}@{hostname}:{port}/{database}'
app.config['JWT_SECRET_KEY'] = jwt_secret_key
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

db.init_app(app)
jwt.init_app(app)
principals = Principal(app)

with app.app_context():
    db.create_all()
    Role.create_default_roles()

from blueprints.auth import auth_bp
from blueprints.sensors import sensors_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(sensors_bp, url_prefix='/sensors')


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    token_type = jwt_payload.get("type")
    if token_type == "access":
        return False

    jti = jwt_payload.get("jti")
    token = TokenWhiteList.query.filter_by(jti=jti).scalar()

    return token is None


@app.before_request
def attach_identity():
    try:
        verify_jwt_in_request(optional=True)
        jwt_data = get_jwt()
        if jwt_data:
            identity = Identity(jwt_data["sub"])
            for role in jwt_data.get("roles", []):
                identity.provides.add(RoleNeed(role))
            identity_changed.send(current_app._get_current_object(), identity=identity)
    except Exception:
        pass


@app.errorhandler(HTTPException)
def handle_permission_errors(e):
    if e.code == 404:
        current_app.logger.warning(f"Not Found: {e}")
        return jsonify({"error": "Not Found"}), 404
    current_app.logger.warning(f"Permission denied: {e}")
    return jsonify({"error": "Permission denied"}), 403


@app.errorhandler(Exception)
def handle_unexpected_errors(e):
    current_app.logger.error(f"Unexpected error: type{type(e)}, message: {e}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
