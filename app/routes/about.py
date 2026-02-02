from flask import Blueprint, render_template, current_app
import os

about_bp = Blueprint("about", __name__, url_prefix="/about")


@about_bp.route("/")
def about_page():
    images = []
    # Фото из static/images/about/
    images_dir = os.path.join(current_app.static_folder, "images", "about")
    if os.path.exists(images_dir):
        images += [
            f"about/{f}"
            for f in os.listdir(images_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))
        ]
    # Фото 01-09.jpg из static/images/
    main_images_dir = os.path.join(current_app.static_folder, "images")
    for i in range(1, 10):
        filename = f"{i:02}.jpg"
        filepath = os.path.join(main_images_dir, filename)
        if os.path.exists(filepath):
            images.append(filename)
    # Видео
    videos = []
    videos_dir = os.path.join(current_app.static_folder, "videos")
    about_videos_dir = os.path.join(videos_dir, "about")
    if os.path.exists(about_videos_dir):
        videos = [
            f
            for f in os.listdir(about_videos_dir)
            if f.lower().endswith((".mp4", ".webm", ".mov", ".avi"))
        ]
    return render_template("about.html", images=images, videos=videos)
