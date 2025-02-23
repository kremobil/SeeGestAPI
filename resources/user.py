import io
from time import sleep

import bcrypt
import requests
from flask.views import MethodView
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, get_jwt
from flask_smorest import Blueprint, abort
from pyexpat.errors import messages
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask import request, jsonify, url_for
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


from db import db
from models import FileModel, UserModel
import os
import magic
from uuid import uuid4

from PIL import Image as PillowImage

from models.blocked_tokens import BlockedTokenModel
from schemas import UserSchema, PlainUserSchema, LoginSchema, AvatarUploadSchema, SocialLoginSchema, \
    ChangePasswordSchema

blp = Blueprint("users", __name__, description="Operations on users")

@blp.route("/register")
class Register(MethodView):

    @blp.arguments(PlainUserSchema(exclude=['birthdate', 'city']), location="json")
    @blp.response(201)
    def post(self, user_data):
        user_data["password"] = bcrypt.hashpw(user_data["password"].encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

        try:
            user = UserModel(**user_data)

            db.session.add(user)
            db.session.commit()
        except IntegrityError as error:
            print(error)
            db.session.rollback()
            abort(400, message=f"User with email {user_data['email']} already exists")
        except SQLAlchemyError as error:
            abort(500, message=f"something went wrong when trying to register")
        return {
            "message": "User registered successfully"
        }

@blp.route("/login")
class Login(MethodView):

    @blp.arguments(LoginSchema(), location="json")
    @blp.response(201, description="user logged in sucessfully")
    def post(self, login_data):
        user = UserModel.query.filter_by(email=login_data["email"]).first()

        # user without password handling (probably created with facebook or google login)

        if user is None:
            abort(401, message="Invalid email or password")

        if user.password is None:
            abort(401, message="Invalid email or password")

        if not bcrypt.checkpw(login_data["password"].encode("utf-8"), user.password.encode("utf-8")):
            abort(401, message="Invalid email or password")

        token = create_access_token(identity=str(user.id))
        return {
            "token": token
        }

@blp.route("/myinfo")
class MyInfo(MethodView):

    @jwt_required()
    @blp.response(200, UserSchema())
    def get(self):
        user_id = get_jwt_identity()
        user = UserModel.query.get_or_404(user_id)
        return user

@blp.route("/google-login")
class GoogleLogin(MethodView):

    @blp.arguments(SocialLoginSchema())
    @blp.response(200)
    def post(self, google_login_data):
        try:
            idinfo = id_token.verify_oauth2_token(google_login_data['token'], google_requests.Request(), os.environ.get("GOOGLE_CLIENT_ID"))

            # Check if user exists in data base and have google account linked
            user = UserModel.query.filter_by(google_user_id=idinfo['sub']).first()

            # if so create jwt token for him
            if user is not None:
                token = create_access_token(identity=str(user.id))
                return {
                    "token": token
                }

            # else chcek if user with google account's email exists in the database
            user = UserModel.query.filter_by(email=idinfo['email']).first()

            # if so chcek if emial is verified if true link google account and return token else abort
            if user is not None:
                if idinfo['email_verified']:
                    user.google_user_id = idinfo['sub']

                    db.session.commit()

                    token = create_access_token(identity=str(user.id))
                    return {
                        "token": token
                    }
                else:
                    abort(401, message="email exists in database but google account is not verified")

            image = requests.get(idinfo['picture']).content

            image_file = FileModel.save_avatar(io.BytesIO(image))

            db.session.add(image_file)

            db.session.commit()

            user = UserModel(email=idinfo['email'], google_user_id=idinfo['sub'], name=idinfo['given_name'], surname=idinfo['family_name'], avatar_id=image_file.id)

            db.session.add(user)

            db.session.commit()

            token = create_access_token(identity=str(user.id))

            return {
                "token": token
            }

        except ValueError as error:
            return jsonify(
                {
                    "message": "Invalid token",
                    "error": str(error)
                }
            )

@blp.route("/facebook-login")
class FacebookLogin(MethodView):
    @blp.arguments(SocialLoginSchema(), location="json")
    @blp.response(200)
    def post(self, social_login_data):
        user_data = requests.get(f"https://graph.facebook.com/v22.0/me?fields=id%2Cfirst_name%2Clast_name%2Cbirthday%2Cemail%2Clocation&access_token={social_login_data['token']}").json()

        user = UserModel.query.filter_by(facebook_user_id=user_data['id']).first()

        if user is not None:
            token = create_access_token(identity=str(user.id))
            return {
                "token": token
            }

        if user_data['email'] is None:
            abort(500, message="Email was not provided by Facebook and you dont have an SeeGest account")

        user = UserModel.query.filter_by(email=user_data['email']).first()

        if user is not None:
            user.facebook_user_id = user_data['id']
            db.session.commit()
            token = create_access_token(identity=str(user.id))
            return {
                "token": token
            }

        profile_pic = requests.get(f"https://graph.facebook.com/v22.0/{user_data['id']}/picture?access_token={social_login_data['token']}")

        avatar = FileModel.save_avatar(io.BytesIO(profile_pic.content))

        db.session.add(avatar)
        db.session.commit()

        user = UserModel(email=user_data['email'], facebook_user_id=user_data['id'], name=user_data['first_name'], surname=user_data['last_name'], avatar_id=avatar.id)

        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))

        return {
            "token": token
        }

@blp.route("/upload-avatar")
class UploadAvatar(MethodView):

    @jwt_required()
    @blp.arguments(AvatarUploadSchema(), location="files")
    @blp.response(201)
    def post(self, image_data):
        file = image_data.get("image")

        image_file = FileModel.save_avatar(file.stream)

        db.session.add(image_file)

        user = UserModel.query.get(get_jwt_identity())

        if user.avatar_id != 1:
            # get old avatar
            old_avatar = FileModel.query.filter_by(id=user.avatar_id).first()

            # override relation to prevent errors
            user.avatar_id = image_file.id

            # remove file and db file record
            file_path = os.path.abspath(os.path.join("static/images", old_avatar.filename))
            os.remove(file_path)
            db.session.delete(old_avatar)

        user.avatar_id = image_file.id

        db.session.commit()

        return {
            "message": "Avatar uploaded successfully"
        }

@blp.route("/complete-profile")
class CompleteProfile(MethodView):

    @jwt_required()
    @blp.arguments(PlainUserSchema(only=['city', 'birthdate']))
    def post(self, user_data):
        user = UserModel.query.get(get_jwt_identity())

        user.city = user_data['city']
        user.birthdate = user_data['birthdate']

        db.session.commit()
        return {
            "message": "Profile complete"
        }

@blp.route("/delete-profile")
class DeleteProfile(MethodView):
    @jwt_required()
    @blp.response(200)
    def delete(self):
        db.session.delete(UserModel.query.get_or_404(get_jwt_identity()))

        blocked_token = BlockedTokenModel(token=get_jwt()['jti'])
        db.session.add(blocked_token)

        db.session.commit()

        return {
            "message": "Profile deleted successfully"
        }

@blp.route("/logout")
class Logout(MethodView):
    @jwt_required()
    @blp.response(201)
    def post(self):
        blocked_token = BlockedTokenModel(token=get_jwt()['jti'])
        db.session.add(blocked_token)
        db.session.commit()

        return {
            "message": "Logged out successful"
        }

@blp.route("/change-password")
class ChangePassword(MethodView):
    @jwt_required()
    @blp.arguments(ChangePasswordSchema(), location="json")
    @blp.response(200)
    def put(self, user_data):
        user = UserModel.query.get(get_jwt_identity())
        if user.password is None:
            abort(401, message="Old password did not match")

        if not bcrypt.checkpw(user_data["old_password"].encode("utf-8"), user.password.encode("utf-8")):
            abort(401, message="Old password did not match")

        if user_data["new_password"] != user_data["new_password_confirmation"]:
            abort(400, message="New password did not match")

        if user_data["new_password"] == user_data["old_password"]:
            abort(400, message="New password can't be the same")

        password_hash = bcrypt.hashpw(user_data["new_password"].encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        user.password = password_hash

        db.session.commit()
        return {
            "message": "Password changed successfully"
        }