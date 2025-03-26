import bcrypt
from flask import Flask, request, jsonify
from model import db
from model.user import User
import os

app = Flask(__name__)

hostname = os.getenv("HOST_DB")
port = os.getenv("PGPORT")
database = os.getenv("POSTGRES_DB")
username = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")

# db = PostgreSQL(hostname=hostname, port=port, database=database, username=username, password=password)

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{username}:{password}@{hostname}:{port}/{database}'

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route('/')
def hello():
    return "Hello World!"


@app.route('/register', methods=['POST'])
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
        existing_user = User.query.filter_by(login=login).first()
    except Exception as e:
        app.logger.error(e)
        return jsonify({"error": "Internal server error"}), 500
    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    try:
        new_user = User(login=login, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return '', 201
    except Exception as e:
        app.logger.error(e)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/login', methods=['POST'])
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
        user = User.query.filter_by(login=login).first()
    except Exception as e:
        app.logger.error(e)
        return jsonify({"error": "Internal server error"}), 500

    if not user:
        return jsonify({"error": "User does not exist"}), 401

    if bcrypt.checkpw(
            password.encode('utf-8'),
            user.password.encode('utf-8')
    ):
        return jsonify({
            "access_token": "",
            "refresh_token": ""
        }), 200
    else:
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
