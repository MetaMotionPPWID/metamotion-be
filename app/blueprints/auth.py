from datetime import datetime
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, decode_token
from model.user import User
from model.token_white_list import TokenWhiteList
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

    User.create_user(login, hashed_password)
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

    user_roles = [role.name for role in user.roles]

    additional_claims = {"roles": user_roles}

    access_token = create_access_token(
        identity=user.login,
        additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(identity=user.login)
    decoded_token = decode_token(refresh_token)

    add_refresh_token_to_white_list(
        user,
        decoded_token.get('jti'),
        decoded_token.get('iat'),
        decoded_token.get('exp')
    )

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
@handle_db_errors
def refresh_access_token():
    identity = get_jwt_identity()
    user = User.get_user_by_username(identity)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_roles = [role.name for role in user.roles]
    additional_claims = {"roles": user_roles}
    new_access_token = create_access_token(
        identity=identity,
        additional_claims=additional_claims
    )
    return jsonify({"access_token": new_access_token}), 200


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


def add_refresh_token_to_white_list(user, jti, iat, exp):
    created_at = datetime.fromtimestamp(iat)
    expires_at = datetime.fromtimestamp(exp)
    tokens = sorted(user.tokens, key=lambda token: token.created_at)
    if len(tokens) >= 10:
        tokens[0].delete()

    new_token = TokenWhiteList(
        jti=jti,
        user_id=user.id,
        created_at=created_at,
        expires_at=expires_at
    )
    new_token.save()
