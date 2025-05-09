import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import warnings
from flask_mail import Message
from dotenv import load_dotenv

from werkzeug.utils import secure_filename
from flask import Flask, redirect
from flask_smorest import Api

import os

from models import FileModel, IconsModel
from models.blocked_tokens import BlockedTokenModel
from resources import UserBlueprint, ImageBlueprint, TagBlueprint, PostBlueprint, LocationBlueprint, IconBlueprint, CommentBlueprint, ReportBlueprint, NotificationBlueprint
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from db import db
from mail import mail
import models

load_dotenv('.flaskenv')

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
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = os.getenv("MAIL_PORT", "587")
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_DEBUG'] = False
    app.config['MAIL_SUPPRESS_SEND'] = False



    api = Api(app)

    #shut down marshmellow warning caused by using it with exclude atribute
    warnings.filterwarnings("ignore", category=UserWarning, message="Multiple schemas resolved*")

    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
        jti = jwt_payload["jti"]
        token = BlockedTokenModel().query.filter_by(token=jti).first()
        return token is not None

    CORS(app, resources={
        r"/*": {
            "origins": ["https://localhost:5173", "https://127.0.0.1:5173"],  # Dodaj używany port Vite
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    db.init_app(app)
    mail.init_app(app)

    with app.app_context():
        db.create_all()
        initial_db_setup()

    api.register_blueprint(UserBlueprint)
    api.register_blueprint(ImageBlueprint)
    api.register_blueprint(TagBlueprint)
    api.register_blueprint(PostBlueprint)
    api.register_blueprint(LocationBlueprint)
    api.register_blueprint(IconBlueprint)
    api.register_blueprint(CommentBlueprint)
    api.register_blueprint(ReportBlueprint)
    api.register_blueprint(NotificationBlueprint)

    @app.route('/')
    def index():
        return redirect("/swagger-ui")

    # Skonfiguruj logowanie
    if not app.debug:
        # Upewnij się, że katalog logów istnieje
        if not os.path.exists('logs'):
            os.mkdir('logs')
    
        # Ustaw plik logu z rotacją (aby uniknąć zbyt dużych plików)
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
         ))
        file_handler.setLevel(logging.INFO)
    
        # Dodaj handler do loggera aplikacji
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Aplikacja startuje')

    # Dodaj globalny handler błędów 500
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {str(error)}')
        return "Internal Server Error", 500

    return app

def initial_db_setup():
    if models.FileModel.query.count() != 0:
        return None
    default_profile_pic = models.FileModel(filename="default_profile.webp", upload_date=datetime.now(), url="https://api.seegest.com/static/images/default_profile.webp", mime_type="image/webp", size=2790)
    db.session.add(default_profile_pic)
    db.session.commit()

    load_icons()

def load_icons():
    print("Loading icons...")
    for file_name in os.listdir(os.path.join("static", "icons")):
        file = FileModel.query.filter_by(filename=file_name).first()
        icon = IconsModel.query.filter_by(name=file_name.split(".")[0].capitalize()).first()

        if not file:
            file = FileModel(filename=file_name, size=os.path.getsize(os.path.join("static", "icons", file_name)),
                             mime_type="image/png", url=f"https://api.seegest.com/static/icons/{file_name}")
            db.session.add(file)
            db.session.commit()

        if icon:
            continue

        icon = IconsModel(name=file_name.split(".")[0].capitalize(), file_id=file.id)
        db.session.add(icon)
        db.session.commit()


if __name__ == "__main__":
    app = create_app()
    # Tworzymy aplikację bazującą na funkcji create_app
    app.run()
