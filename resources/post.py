from calendar import monthrange
from collections import defaultdict

from sqlalchemy import func, and_

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from datetime import date, timedelta, datetime

from db import db
from models import TagsModel, PostModel, UserModel
from schemas import PostSchema, SearchPostSchema, PostCalendarSearchSchema, PostCalendarPreviewSchema

blp = Blueprint('posts', __name__)

@blp.route('/posts')
class Posts(MethodView):

    @jwt_required()
    @blp.arguments(PostSchema())
    @blp.response(201, PostSchema())
    def post(self, post_data: dict):
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
            is_anonymous=post_data.get('is_anonymous'),
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
        if post.tags:
            for tag in post.tags:
                tag.count -= 1
        user = UserModel.query.get(get_jwt_identity())
        if str(post.author_id) != user.id and not (user.is_admin or user.is_super_admin):
            abort(403, message="You are not authorized to perform this action")
        db.session.delete(post)
        db.session.commit()

        return {
            "message": f"Post {post_id} deleted",
        }

    @blp.response(200, PostSchema())
    def get(self, post_id):
        return PostModel.query.get_or_404(post_id)

@blp.route("/search-posts")
class SearchPosts(MethodView):
    @blp.arguments(SearchPostSchema(), location="json")
    @blp.response(200, PostSchema(many=True))
    def post(self, search_data):
        posts = PostModel.query

        today = date.today()

        if search_data.get('date_from'):
            posts = posts.filter(PostModel.created_at >= search_data['date_from'])
        else:
            date_from = datetime(today.year, today.month, today.day, 0, 0, 0)
            posts = posts.filter(PostModel.created_at >= date_from)

        if search_data.get('date_to'):
            posts = posts.filter(PostModel.created_at <= search_data['date_to'])
        else:
            date_to = datetime(today.year, today.month, today.day, 23, 59, 59)
            posts = posts.filter(PostModel.created_at <= date_to)

        if search_data.get('tags_ids'):
            posts = posts.join(PostModel.tags).filter(TagsModel.id.in_(search_data['tags_ids'])).group_by(PostModel.id).having(db.func.count(TagsModel.id) == len(search_data['tags_ids']))

        if search_data.get('position'):
            lat, lon = search_data['position']['latitude'], search_data['position']['longitude']
            posts = posts.order_by(PostModel.distance_to(lat, lon))

        return posts.all()


@blp.route("/calendar-preview")
class PostCalendarPreview(MethodView):
    @blp.arguments(PostCalendarSearchSchema(), location="json")
    @blp.response(200, PostCalendarPreviewSchema())
    def post(self, search_data):
        base_date = date(search_data['year'], search_data['month'], 1)
        offset_months = search_data.get('offset', 0)

        start_date = add_months(base_date, -offset_months)

        end_month_start = add_months(base_date, offset_months + 1)
        end_date = end_month_start - timedelta(days=1)

        posts = PostModel.query.with_entities(
            PostModel.id,
            PostModel.title,
            PostModel.created_at
        ).filter(
            and_(
                PostModel.created_at >= start_date,
                PostModel.created_at <= end_date
            )
        )

        if search_data.get('start_time'):
            print(type(search_data['start_time']))
            posts = posts.filter(
                func.time(PostModel.created_at) >= search_data['start_time']
            )

        if search_data.get('end_time'):
            posts = posts.filter(
                func.time(PostModel.created_at) <= search_data['end_time']
            )

        if search_data.get('tags_ids'):
            posts = (
                posts
                .join(PostModel.tags)
                .filter(TagsModel.id.in_(search_data['tags_ids']))
                .group_by(PostModel.id, PostModel.title, PostModel.created_at)
                .having(func.count(TagsModel.id) == len(search_data['tags_ids']))
            )

        results = posts.all()
        posts_by_date = defaultdict(list)

        for post in results:

            date_key = date(post.created_at.year, post.created_at.month, post.created_at.day)
            posts_by_date[date_key].append({
                'id': post.id,
                'title': post.title,
                'created_at': post.created_at
            })

        calendar_data = {
            'meta': {
                'start_date': start_date,
                'end_date': end_date,
                'total_posts': len(results)
            },
            'dates': {
                date: {
                    'count': len(posts),
                    'posts': posts
                }
                for date, posts in posts_by_date.items()
            }
        }

        return calendar_data

def add_months(source_date: date, months: int) -> date:
    """Dodaje lub odejmuje miesiące od daty"""
    year = source_date.year + ((source_date.month + months - 1) // 12)
    month = ((source_date.month + months - 1) % 12) + 1
    # Upewniamy się, że dzień jest prawidłowy dla nowego miesiąca
    day = min(source_date.day, monthrange(year, month)[1])
    return date(year, month, day)