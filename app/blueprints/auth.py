from flask import Blueprint, request, jsonify, current_app
import bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token
from model.user import User
from schemas.user_schema import UserSchema
from utils.handle_errors import handle_db_errors, handle_validation_errors

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@handle_validation_errors
@handle_db_errors
def register():
    data = UserSchema().load(request.get_json())

    login = data.get('login')
    password = data.get('password')

    existing_user = User.get_user_by_username(login)
    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    hashed_password = hash_password(password)

    new_user = User(login=login, password=hashed_password)
    new_user.save()
    return '', 201


@auth_bp.route('/login', methods=['POST'])
@handle_validation_errors
@handle_db_errors
def login():
    data = UserSchema().load(request.get_json())

    login = data.get("login")
    password = data.get("password")

    user = User.get_user_by_username(login)

    if not user or not verify_password(password, user.password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.login)
    refresh_token = create_refresh_token(identity=user.login)
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200


def hash_password(password):
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
