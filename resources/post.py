from operator import indexOf

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint, abort
from flask.views import MethodView

from db import db
from models import TagsModel, PostsModel
from schemas import PostSchema

blp = Blueprint('post', __name__)

@blp.route('/post')
class Post(MethodView):

    @jwt_required()
    @blp.arguments(PostSchema())
    @blp.response(201, PostSchema())
    def post(self, post_data):
        tags_list = list(map(lambda tag_id: TagsModel.query.get(tag_id), post_data['tags_ids']))

        if None in tags_list:
            abort(400, message=f"Tag with id {post_data['tags_ids'][tags_list.index(None)]} not found")

        for tag in tags_list:
            tag.count += 1

        post = PostsModel(
            title=post_data['title'],
            content=post_data['content'],
            tags=tags_list,
            author_id=get_jwt_identity(),
            created_at=post_data['created_at'],
            location=post_data['location'],
            icon_id=post_data['icon_id'],
        )

        db.session.add(post)
        db.session.commit()

        return post

    @jwt_required()
    @blp.response(200, PostSchema(many=True))
    def get(self):
        return PostsModel.query.all()
