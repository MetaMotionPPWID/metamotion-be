from flask import Flask
from blueprints.auth import auth_bp
from model import db
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

app.register_blueprint(auth_bp, url_prefix='/auth')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
