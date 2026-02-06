import datetime
import io
import re
from time import sleep

import bcrypt
import requests
from flask.views import MethodView
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, get_jwt
from flask_mail import Message
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask import request, jsonify, url_for, render_template
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


from db import db
from mail import mail
from models import FileModel, UserModel, BlockedTokenModel, PasswordResetModel
import os
import magic
from uuid import uuid4

from PIL import Image as PillowImage

from schemas import UserSchema, PlainUserSchema, LoginSchema, AvatarUploadSchema, SocialLoginSchema, \
    ChangePasswordSchema, ResetPasswordSchema

blp = Blueprint("users", __name__, description="Operations on users")

ALLOWED_GOOGLE_CLIENT_IDS = (
        os.environ.get("GOOGLE_CLIENT_ID_WEB"),
        os.environ.get("GOOGLE_CLIENT_ID_ANDROID"),
        os.environ.get("GOOGLE_CLIENT_ID_IOS")
    )

@blp.route("/register")
class Register(MethodView):

    @blp.arguments(PlainUserSchema(exclude=['birthdate', 'city']), location="json")
    @blp.response(201)
    def post(self, user_data):
        capital_regex = re.compile(r'[A-Z]')

        if not capital_regex.search(user_data["password"]):
            abort(422, message="Password should contain at least one capital letter")

        lower_regex = re.compile(r"[a-z]")

        if not lower_regex.search(user_data["password"]):
            abort(422, message="Password should contain at least one lowercase letter")

        number_regex = re.compile(r"[0-9]")

        if not number_regex.search(user_data["password"]):
            abort(422, message="Password should contain at least one number")

        special_regex = re.compile(r"[^a-zA-Z0-9 \n]")

        if not special_regex.search(user_data["password"]):
            abort(422, message="Password should contain at least one special character and cannot contain whitespace")

        if not len(user_data["password"]) > 8:
            abort(422, message="Password should contain at least 8 characters")

        user_data["password"] = bcrypt.hashpw(user_data["password"].encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

        try:
            user = UserModel(**user_data)

            db.session.add(user)
            db.session.commit()
        except IntegrityError as error:
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

@blp.route("/profile-completed")
class ProfileCompleted(MethodView):
    @jwt_required()
    @blp.response(200, description="Profile is complete")
    @blp.alt_response(400, description="Profile was not completed yet")
    def get(self):
        user_id = get_jwt_identity()
        user = UserModel.query.get_or_404(user_id)
        if user.birthdate is None or user.city is None:
            abort(400, message="Profile not completed birthdate or city are not provided")
        return {
            "message": "Profile is complete"
        }, 200

@blp.route("/google-login")
class GoogleLogin(MethodView):

    @blp.arguments(SocialLoginSchema())
    @blp.response(200)
    def post(self, google_login_data):
        try:
            idinfo = id_token.verify_oauth2_token(google_login_data['token'], google_requests.Request(), os.environ.get("GOOGLE_CLIENT_ID"))

            if idinfo['aud'] not in ALLOWED_GOOGLE_CLIENT_IDS:
                abort(401, message=f"Invalid client: {idinfo['aud']}")

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

@blp.route('/google-link')
class GoogleConnect(MethodView):

    @jwt_required()
    @blp.arguments(SocialLoginSchema(), location="json")
    @blp.response(200, description="Google account connected")
    def post(self, google_login_data):
        idinfo = id_token.verify_oauth2_token(google_login_data['token'], google_requests.Request(),
                                              os.environ.get("GOOGLE_CLIENT_ID"))

        if idinfo['aud'] not in ALLOWED_GOOGLE_CLIENT_IDS:
            abort(401, message=f"Invalid client: {idinfo['aud']}")

        # Check if user exists in data base and have google account linked
        user = UserModel.query.filter_by(google_user_id=idinfo['sub']).first()

        if user is not None:
            abort(401, message="This account is already connected to other user's account")

        user = UserModel.query.get(get_jwt_identity())
        user.google_user_id = idinfo['sub']
        db.session.commit()

        return {
            "message": "Google connected successfully"
        }

@blp.route('/google-unlink')
class GoogleUnlink(MethodView):

    @jwt_required()
    @blp.response(200, description="Google account unlinked")
    def post(self):
        user = UserModel.query.get(get_jwt_identity())
        user.google_user_id = None
        db.session.commit()

        return {
            "message": "Google unlinked successfully"
        }

@blp.route("/send-reset-code")
class SendResetCode(MethodView):

    @blp.arguments(LoginSchema(only=["email"]), location="json")
    def post(self, user_data):
        user = UserModel.query.filter_by(email=user_data["email"]).first()
        if user:
            if user.password_reset_code:
                db.session.delete(user.password_reset_code[0])
                db.session.commit()

            reset_code = uuid4()
            code = PasswordResetModel(user_id=user.id, code=str(reset_code))
            db.session.add(code)
            db.session.commit()
            msg = Message(
                subject="Zresetuj hasło",
                recipients=[user_data["email"]],
            )
            msg.html = render_template("password_recovery.html", title="Password recovery", reset_code=code.code)
            msg.attach("logo.png", "image/png", open(os.path.join("static", "mails", "logo.png"), 'rb').read(), 'inline', headers={
                "Content-ID": "<logo>",
            })
            mail.send(msg)
        return "sucess", 200

@blp.route("/reset-password")
class ResetPassword(MethodView):
    @blp.arguments(ResetPasswordSchema(), location="json")
    @blp.response(201, description="User password reset sucessfully")
    def post(self, reset_data):
        user = UserModel.query.filter_by(email=reset_data["email"]).first()

        if not user:
            abort(401, message="This code does not belong to this email")

        if not user.password_reset_code:
            abort(401, message="This code does not belong to this email")

        if user.password_reset_code[0].code != reset_data["code"]:
            user.password_reset_code[0].number_of_attempts += 1
            db.session.commit()

            if user.password_reset_code[0].number_of_attempts >= 8:
                db.session.delete(user.password_reset_code[0])
                db.session.commit()
            abort(401, message="This code does not belong to this email")

        capital_regex = re.compile(r"[A-Z]")

        if not capital_regex.search(reset_data["new_password"]):
            abort(422, message="Password should contain at least one capital letter")

        lower_regex = re.compile(r"[a-z]")

        if not lower_regex.search(reset_data["new_password"]):
            abort(422, message="Password should contain at least one lowercase letter")

        number_regex = re.compile(r"[0-9]")

        if not number_regex.search(reset_data["new_password"]):
            abort(422, message="Password should contain at least one number")

        special_regex = re.compile(r"[^a-zA-Z0-9 \n]")

        if not special_regex.search(reset_data["new_password"]):
            abort(422, message="Password should contain at least one special character and cannot contain whitespace")

        if not len(reset_data["new_password"]) >= 8:
            abort(422, message="Password should contain at least 8 characters")

        password = bcrypt.hashpw(reset_data["new_password"].encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

        user.password = password

        db.session.delete(user.password_reset_code[0])
        db.session.commit()

        return {
            "message": "Password has been changed successfully"
        }

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

        if user_data.get('email') is None:
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

@blp.route("/facebook-link")
class FacebookConnect(MethodView):

    @jwt_required()
    @blp.arguments(SocialLoginSchema(), location="json")
    @blp.response(200)
    def post(self, social_login_data):
        user_data = requests.get(f"https://graph.facebook.com/v22.0/me?fields=id%2Cfirst_name%2Clast_name%2Cbirthday%2Cemail%2Clocation&access_token={social_login_data['token']}").json()

        if UserModel.query.filter_by(facebook_user_id=user_data['id']).first() is not None:
            abort(401, message="This facebook account is already linked to other users account")

        user = UserModel.query.get(get_jwt_identity())

        user.facebook_user_id = user_data['id']

        db.session.commit()

        return {
            "message": "Facebook connected successfully"
        }

@blp.route("/facebook-unlink")
class FacebookUnlink(MethodView):
    @jwt_required()
    @blp.response(200, description="Facebook account unlinked")
    def post(self):
        user = UserModel.query.get(get_jwt_identity())
        user.facebook_user_id = None
        db.session.commit()

        return {
            "message": "Facebook unlinked successfully"
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
        if ((datetime.datetime.now().year - user_data['birthdate'].year) > 120):
            abort(422, message="Birth date is too far")

        if not((datetime.datetime.now().year - user_data['birthdate'].year) >= 13 and datetime.datetime.now().month >= user_data['birthdate'].month and datetime.datetime.now().day >= user_data['birthdate'].day):
            abort(422, message="User have to be at least 13 years old")

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

        capital_regex = re.compile(r"[A-Z]")

        if not capital_regex.search(user_data["new_password"]):
            abort(422, message="Password should contain at least one capital letter")

        lower_regex = re.compile(r"[a-z]")

        if not lower_regex.search(user_data["new_password"]):
            abort(422, message="Password should contain at least one lowercase letter")

        number_regex = re.compile(r"[0-9]")

        if not number_regex.search(user_data["new_password"]):
            abort(422, message="Password should contain at least one number")

        special_regex = re.compile(r"[^a-zA-Z0-9 \n]")

        if not special_regex.search(user_data["new_password"]):
            abort(422, message="Password should contain at least one special character and cannot contain whitespace")

        if not len(user_data["new_password"]) > 8:
            abort(422, message="Password should contain at least 8 characters")

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