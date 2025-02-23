from operator import indexOf

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint, abort
from flask.views import MethodView

from db import db
from models import TagsModel, PostModel, UserModel
from schemas import PostSchema, SearchPostSchema

blp = Blueprint('posts', __name__)

@blp.route('/posts')
class Posts(MethodView):

    @jwt_required()
    @blp.arguments(PostSchema())
    @blp.response(201, PostSchema())
    def post(self, post_data):
        tags_list = list(map(lambda tag_id: TagsModel.query.get(tag_id), post_data['tags_ids']))

        if None in tags_list:
            abort(400, message=f"Tag with id {post_data['tags_ids'][tags_list.index(None)]} not found")

        for tag in tags_list:
            tag.count += 1

        post = PostModel(
            title=post_data['title'],
            content=post_data['content'],
            tags=tags_list,
            author_id=get_jwt_identity(),
            created_at=post_data['created_at'],
            location=post_data['location'],
            icon_id=post_data['icon_id'],
            longitude=post_data['longitude'],
            latitude=post_data['latitude'],
        )

        db.session.add(post)
        db.session.commit()

        return post

    @jwt_required()
    @blp.response(200, PostSchema(many=True))
    def get(self):
        return PostModel.query.all()

@blp.route("/post/<int:post_id>")
class Post(MethodView):
    @jwt_required()
    @blp.response(200)
    def delete(self, post_id):
        post = PostModel.query.get_or_404(post_id)
        user = UserModel.query.get(get_jwt_identity())
        if str(post.author_id) != user.id and not (user.is_admin or user.is_super_admin):
            abort(403, message="You are not authorized to perform this action")
        db.session.delete(post)
        db.session.commit()

        return {
            "message": f"Post {post_id} deleted",
        }

@blp.route("/search-posts")
class SearchPosts(MethodView):
    @jwt_required()
    @blp.arguments(SearchPostSchema(), location="json")
    @blp.response(200, PostSchema(many=True))
    def get(self, search_data):
        posts = PostModel.query

        if search_data.get('date_from'):
            posts = posts.filter(PostModel.created_at >= search_data['date_from'])

        if search_data.get('date_to'):
            posts = posts.filter(PostModel.created_at <= search_data['date_to'])

        if search_data.get('tags_ids'):
            posts = posts.join(PostModel.tags).filter(TagsModel.id.in_(search_data['tags_ids'])).group_by(PostModel.id).having(db.func.count(TagsModel.id) == len(search_data['tags_ids']))

        if search_data.get('position'):
            lat, lon = search_data['position']['latitude'], search_data['position']['longitude']
            posts = posts.order_by(PostModel.distance_to(lat, lon))
            
        return posts.all()