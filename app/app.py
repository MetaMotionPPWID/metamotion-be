from datetime import datetime

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
