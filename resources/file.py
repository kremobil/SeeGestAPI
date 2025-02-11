import io

from flask.views import MethodView
from flask_smorest import abort, Blueprint
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import FileModel, UserModel
from schemas import PlainFileSchema
import os


blp = Blueprint("files", __name__, description="Operations on images")

@blp.route("/files")
class FileList(MethodView):

    @blp.response(201, PlainFileSchema(many=True))
    def get(self):
        return FileModel.query.all()

@blp.route("/files/<int:file_id>")
class File(MethodView):
    def get(self, file_id):
        return FileModel.query.get_or_404(file_id)

    def delete(self, file_id):
        file = FileModel.query.get_or_404(file_id)
        try:
            user = UserModel.query.filter_by(avatar_id=file_id).first()
            if user is not None:
                user.avatar_id = 1
            os.remove(os.path.join("static", "images", file.filename))
            db.session.add(user)
            db.session.delete(file)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, message=f"Something went wrong when trying to delete file {file_id}")
        except Exception as e:
            abort(500, message=f"Something went wrong when trying to delete file {file_id}: {str(e)}")
        return {
            "message": f"File {file_id} deleted successfully"
        }




