from flask import Blueprint, request, jsonify, current_app
import bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token
from model.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required_params = {
        "login": str,
        "password": str
    }
    errors = validation(data, required_params)
    if errors:
        return jsonify({"error": errors}), 400

    login = request.json.get("login")
    password = request.json.get("password")

    if len(login) < 7 or len(login) > 60:
        return jsonify({"error": "Login must be between 7 and 60 characters"}), 400
    if len(password) < 7:
        return jsonify({"error": "Password must have at least 7 characters"}), 400

    try:
        existing_user = User.get_user_by_username(login)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify({"error": "Internal server error"}), 500
    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    try:
        new_user = User(login=login, password=hashed_password)
        new_user.save()
        return '', 201
    except Exception as e:
        current_app.logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    required_params = {
        "login": str,
        "password": str
    }
    errors = validation(data, required_params)
    if errors:
        return jsonify({"error": errors}), 400

    login = request.json.get("login")
    password = request.json.get("password")

    try:
        user = User.get_user_by_username(login)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify({"error": "Internal server error"}), 500

    if not user:
        return jsonify({"error": "User does not exist"}), 404

    if bcrypt.checkpw(
            password.encode('utf-8'),
            user.password.encode('utf-8')
    ):
        access_token = create_access_token(identity=user.login)
        refresh_token = create_refresh_token(identity=user.login)
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200

    return jsonify({"error": "Invalid password"}), 401


def validation(data, required_params):
    errors = []
    for param, expected_type in required_params.items():
        if param not in data:
            errors.append(f"Missing parameter: {param}")
        elif not isinstance(data[param], expected_type):
            errors.append(
                f"Invalid type of parameter: {param}. Expected {expected_type}, received {type(data[param]).__name__}")
    return errors
