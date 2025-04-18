from flask import Blueprint, render_template, abort
from app.models import BlogPost

blog_bp = Blueprint('blog', __name__, template_folder='../templates')

@blog_bp.route("/")
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("blog.html", posts=posts)

@blog_bp.route("/<slug>")
def post(slug):
    post = BlogPost.query.filter_by(slug=slug).first()
    if not post:
        abort(404)
    return render_template("post.html", post=post)
