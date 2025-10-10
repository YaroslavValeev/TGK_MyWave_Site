from flask import Blueprint, render_template, abort, request, jsonify
from app.database.models import BlogPost
from datetime import datetime

blog_bp = Blueprint('blog', __name__, template_folder='../templates')

@blog_bp.route("/")
def blog():
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Можно изменить на нужное количество
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template("blog.html", posts=posts)

@blog_bp.route("/<slug>")
def post(slug):
    post = BlogPost.query.filter_by(slug=slug).first()
    if not post:
        abort(404)
    return render_template("post.html", post=post)

@blog_bp.route("/api/latest")
def get_latest_post():
    """API endpoint для получения последней статьи"""
    try:
        latest_post = BlogPost.query.order_by(BlogPost.created_at.desc()).first()
        if not latest_post:
            return jsonify({"error": "No posts found"}), 404
            
        return jsonify({
            "title": latest_post.title,
            "date": latest_post.created_at.isoformat(),
            "content": latest_post.content,
            "slug": latest_post.slug
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
