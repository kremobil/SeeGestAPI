from datetime import datetime
import warnings

from flask import Flask
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.testing.config import db_url
from resources import UserBlueprint, ImageBlueprint, TagBlueprint, PostBlueprint, LocationBlueprint
from flask_jwt_extended import JWTManager
import os
from flask_cors import CORS

from db import db
import models


def create_app(db_url=None):
    app = Flask(__name__)

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["API_TITLE"] = "SeeGest API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or os.getenv("DATABASE_URL", "sqlite:///seegest.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")
    db.init_app(app)

    api = Api(app)

    #shut down marshmellow warning caused by using it with exclude atribute
    warnings.filterwarnings("ignore", category=UserWarning, message="Multiple schemas resolved*")

    jwt = JWTManager(app)

    CORS(app, resources={
        r"/*": {
            "origins": ["https://localhost:5173", "https://127.0.0.1:5173"],  # Dodaj używany port Vite
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    with app.app_context():
        db.create_all()
        initial_db_setup(db)

    api.register_blueprint(UserBlueprint)
    api.register_blueprint(ImageBlueprint)
    api.register_blueprint(TagBlueprint)
    api.register_blueprint(PostBlueprint)
    api.register_blueprint(LocationBlueprint)

    return app

def initial_db_setup(db: SQLAlchemy):
    if models.FileModel.query.count() == 0:
        return None
    default_profile_pic = models.FileModel(filename="default_profile.webp", upload_date=datetime.now(), url="https://127.0.0.1:5000/static/images/default_profile.webp", mime_type="image/webp", size=2790)
    db.session.add(default_profile_pic)
    db.session.commit()

if __name__ == "__main__":
    app = create_app()  # Tworzymy aplikację bazującą na funkcji create_app
    app.run()
