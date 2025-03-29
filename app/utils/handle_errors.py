from functools import wraps
from flask import jsonify, current_app
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError


def handle_db_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            current_app.logger.error(f"DB error: {e}")
            return jsonify({"error": "Internal server error"}), 500
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {e}")
            return jsonify({"error": "Internal server error"}), 500

    return wrapper


def handle_validation_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            current_app.logger.warning(f"Validation error: {e.messages}")
            return jsonify({"error": e.messages}), 400

    return wrapper
