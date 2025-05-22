import os
from datetime import timedelta
from flask import Flask, current_app, jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_principal import Principal, RoleNeed, Identity, identity_changed
from werkzeug.exceptions import HTTPException

from app.extension import db, jwt, api, migrate
from app.model.role import Role
from app.model.token_white_list import TokenWhiteList
from app.blueprints.auth import auth_bp
from app.blueprints.sensors import sensors_bp
from app.blueprints.cli import seed_db


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
    ).replace("postgres://", "postgresql://")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)

    db.init_app(app)
    jwt.init_app(app)
    api.init_app(app)
    migrate.init_app(app, db)
    principals = Principal(app)

    api.add_namespace(auth_bp, path="/auth")
    api.add_namespace(sensors_bp, path="/sensors")

    # Register CLI commands
    app.cli.add_command(seed_db)

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
                identity_changed.send(
                    current_app._get_current_object(), identity=identity
                )
        except Exception:
            pass

    @app.errorhandler(HTTPException)
    def handle_permission_errors(e):
        if e.code == 404:
            current_app.logger.warning(f"Not Found: {e}")
            return jsonify({"error": "Not Found"}), 404
        elif e.code == 422:
            current_app.logger.warning(f"Unprocessable Entity: {e}")
            return jsonify({"error": "Unprocessable Entity"}), 422
        current_app.logger.warning(f"Permission denied: {e}")
        return jsonify({"error": "Permission denied"}), 403

    @app.errorhandler(Exception)
    def handle_unexpected_errors(e):
        current_app.logger.error(f"Unexpected error: type{type(e)}, message: {e}")
        return jsonify({"error": "Internal server error"}), 500

    return app
