from flask import Flask
from extension import db, jwt
import os
from datetime import timedelta


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

with app.app_context():
    db.create_all()

from blueprints.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
