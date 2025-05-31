from datetime import datetime
from flask import request
import bcrypt
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    decode_token,
)
from app.model.user import User
from app.model.token_white_list import TokenWhiteList
from app.utils.handle_errors import handle_db_errors, handle_validation_errors

auth_bp = Namespace("auth", description="Authentication related endpoints")

# Schema definitions
user_schema = auth_bp.model(
    "User",
    {
        "login": fields.String(
            required=True,
            min_length=7,
            max_length=60,
            description="The login of the user",
        ),
        "password": fields.String(
            required=True,
            min_length=7,
            max_length=60,
            description="The password of the user",
        ),
    },
)

token_schema = auth_bp.model(
    "Token",
    {
        "access_token": fields.String(required=True, description="The access token"),
        "refresh_token": fields.String(required=True, description="The refresh token"),
    },
)

refresh_token_schema = auth_bp.model(
    "RefreshToken",
    {"refresh_token": fields.String(required=True, description="The refresh token")},
)


@auth_bp.route("/register")
class Register(Resource):
    @auth_bp.expect(user_schema)
    @handle_validation_errors
    @handle_db_errors
    def post(self):
        data = auth_bp.payload
        login = data.get("login")
        password = data.get("password")

        existing_user = User.get_user_by_username(login)
        if existing_user:
            return {"error": "User already exists"}, 400

        hashed_password = hash_password(password)

        User.create_user(login, hashed_password)
        return "", 201


@auth_bp.route("/login")
class Login(Resource):
    @auth_bp.expect(user_schema)
    @auth_bp.marshal_with(token_schema)
    @handle_validation_errors
    @handle_db_errors
    def post(self):
        data = auth_bp.payload

        login = data.get("login")
        password = data.get("password")

        user = User.get_user_by_username(login)

        if not user or not verify_password(password, user.password):
            return {"error": "Invalid credentials"}, 401

        user_roles = [role.name for role in user.roles]

        additional_claims = {"roles": user_roles}

        access_token = create_access_token(
            identity=user.login, additional_claims=additional_claims
        )
        refresh_token = create_refresh_token(identity=user.login)
        decoded_token = decode_token(refresh_token)

        add_refresh_token_to_white_list(
            user,
            decoded_token.get("jti"),
            decoded_token.get("iat"),
            decoded_token.get("exp"),
        )

        return {"access_token": access_token, "refresh_token": refresh_token}


@auth_bp.route("/refresh")
class Refresh(Resource):
    @jwt_required(refresh=True)
    @auth_bp.marshal_with(token_schema)
    @handle_db_errors
    def post(self):
        identity = get_jwt_identity()

        user = User.get_user_by_username(identity)
        if not user:
            return {"error": "User not found"}, 404
        user_roles = [role.name for role in user.roles]
        additional_claims = {"roles": user_roles}
        new_access_token = create_access_token(
            identity=identity, additional_claims=additional_claims
        )
        return {"access_token": new_access_token}


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def add_refresh_token_to_white_list(user, jti, iat, exp):
    created_at = datetime.fromtimestamp(iat)
    expires_at = datetime.fromtimestamp(exp)
    tokens = sorted(user.tokens, key=lambda token: token.created_at)
    if len(tokens) >= 10:
        tokens[0].delete()

    new_token = TokenWhiteList(
        jti=jti, user_id=user.id, created_at=created_at, expires_at=expires_at
    )
    new_token.save()
