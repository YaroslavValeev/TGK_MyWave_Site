import sys
from datetime import datetime
from flask import current_app
from app import create_app, db
from app.models import BlogPost, ChatMessage

def add_post(title, teaser, content, slug):
    app = create_app()
    with app.app_context():
        # Проверка на уникальность slug
        if BlogPost.query.filter_by(slug=slug).first():
            print(f"Пост с таким slug уже существует: {slug}")
            return

        post = BlogPost(
            title=title,
            teaser=teaser,
            content=content,
            slug=slug,
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()

        # Добавляем сообщение в чат
        chat_msg = ChatMessage(
            user='bot',
            message=f"📝 Новая статья: <b>{title}</b>\n{teaser}",
            created_at=datetime.utcnow(),
            blog_post_id=post.id
        )
        db.session.add(chat_msg)
        db.session.commit()
        print(f"Пост '{title}' и сообщение в чат успешно добавлены.")

if __name__ == "__main__":
    # Пример запуска: python scripts/add_post.py "Заголовок" "Тизер" "Контент" "slug"
    if len(sys.argv) != 5:
        print("Использование: python scripts/add_post.py 'Заголовок' 'Тизер' 'Контент' 'slug'")
        sys.exit(1)
    add_post(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
