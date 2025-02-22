from db import db
from flask_smorest import abort

import magic
from PIL import Image as PillowImage
from uuid import uuid4
import io, os

class FileModel(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    mime_type = db.Column(db.String(50), nullable=False)
    size = db.Column(db.Integer, nullable=False)

    @classmethod
    def save_avatar(cls, file_stream: io.BytesIO):
        if (magic.from_buffer(file_stream.read(), mime=True) not in (
        "image/png", "image/jpeg", "image/webp", "image/jpg")):
            abort(400, message="Invalid image format, available formats: png, jpg, jpeg, webp")

        file_stream = file_stream

        img = PillowImage.open(file_stream)  # Pillow obsługuje bezpośrednio strumienie

        img.convert("RGB")

        width, height = img.size

        new_edge = min(width, height)

        left = (width - new_edge) // 2
        top = (height - new_edge) // 2
        right = left + new_edge
        bottom = top + new_edge

        img_cropped = img.crop((left, top, right, bottom))

        # Skalowanie do 128x128
        img_resized = img_cropped.resize((128, 128), PillowImage.LANCZOS)

        filename = uuid4().hex + ".webp"
        os.makedirs("/static/images", exist_ok=True)

        save_path = os.path.join("static", "images", filename)
        img_resized.save(save_path, format="WEBP")

        return  cls(filename=filename, url=f"https://127.0.0.1:5000/{save_path}", mime_type="image/webp",
                               size=os.path.getsize(save_path))
    
    