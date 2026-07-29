"""
Пакет для административных маршрутов
"""
import os
from flask import Blueprint, render_template, current_app, abort, flash, redirect, request, url_for
from flask_login import login_required
from app.database.models import BlogPost, CalendarEvent, User, Image
from app.utils.decorators import admin_required

bp = Blueprint('admin', __name__, url_prefix='/admin')


def _safe_count(model, default=0):
    """Безопасный подсчёт записей модели."""
    try:
        return model.query.count()
    except Exception:
        return default


def _count_images_in_folder(static_folder, default=0):
    """Подсчёт файлов изображений в папке static/images."""
    try:
        images_dir = os.path.join(static_folder, 'images')
        if os.path.isdir(images_dir):
            return sum(1 for f in os.listdir(images_dir)
                       if os.path.isfile(os.path.join(images_dir, f)))
    except Exception:
        pass
    return default


def _load_blog_posts_for_admin(limit: int = 50):
    try:
        from app.services.blog.store import get_posts

        posts, total = get_posts(page=1, limit=limit, prefer_sheets=True)
        return posts or [], total, "Sheets / raw_feed (+ DB fallback)"
    except Exception as exc:
        current_app.logger.warning("admin_blog_list_store_failed err=%s", exc)
        try:
            rows = (
                BlogPost.query.order_by(BlogPost.published_at.desc().nullslast(), BlogPost.id.desc())
                .limit(limit)
                .all()
            )
            posts = [
                {
                    "title": r.title,
                    "slug": r.slug,
                    "status": r.status,
                    "published_at": r.published_at.isoformat() if r.published_at else "",
                    "source_name": r.source_name,
                    "source_type": r.source_type,
                }
                for r in rows
            ]
            return posts, len(posts), "DB BlogPost (fallback)"
        except Exception as db_exc:
            current_app.logger.warning("admin_blog_list_db_failed err=%s", db_exc)
            return [], 0, "unavailable"


def _settings_flag_rows():
    rows = []
    try:
        from app.config.social_features import get_social_feature_flags

        for key, value in get_social_feature_flags().items():
            rows.append({"key": key, "value": bool(value), "note": "Social Mission"})
    except Exception:
        pass
    try:
        from app.config.online_coaching_features import get_online_coaching_feature_flags

        for key, value in get_online_coaching_feature_flags().items():
            rows.append({"key": key, "value": bool(value), "note": "Online Coaching"})
    except Exception:
        pass
    try:
        from app.config.camp_features import get_camp_feature_flags

        for key, value in get_camp_feature_flags().items():
            rows.append({"key": key, "value": bool(value), "note": "Camp (public/import OFF until GO)"})
    except Exception:
        pass

    try:
        from app.config.blog_features import is_blog_admin_write_enabled

        rows.append({
            "key": "BLOG_ADMIN_WRITE_ENABLED",
            "value": is_blog_admin_write_enabled(),
            "note": "B4 Admin writeback SEO/карточки в raw_feed",
        })
    except Exception:
        pass

    rows.append({
        "key": "ENABLE_GOOGLE_SERVICES",
        "value": bool(current_app.config.get("ENABLE_GOOGLE_SERVICES")),
        "note": "Google Sheets / Calendar integrations",
    })
    yclients = str(os.getenv("YCLIENTS_ENABLED", "0")).strip().lower() in ("1", "true", "yes", "on")
    rows.append({
        "key": "YCLIENTS_ENABLED",
        "value": yclients,
        "note": "YClients boat SoT",
    })
    yclients_write = str(os.getenv("YCLIENTS_WRITE_ENABLED", "0")).strip().lower() in ("1", "true", "yes", "on")
    rows.append({
        "key": "YCLIENTS_WRITE_ENABLED",
        "value": yclients_write,
        "note": "YClients controlled writes",
    })
    return rows


@bp.route('/')
@login_required
@admin_required
def index():
    """
    Главная страница административной панели
    """
    blog_posts_count = _safe_count(BlogPost)
    events_count = _safe_count(CalendarEvent)
    users_count = _safe_count(User)
    images_model_count = _safe_count(Image)
    images_count = images_model_count if images_model_count > 0 else _count_images_in_folder(
        current_app.static_folder
    )
    recent_actions = [
        {'icon': 'save', 'time': 'Сейчас', 'title': 'Админка', 'description': 'Панель управления загружена'},
    ]
    return render_template(
        'admin/index.html',
        blog_posts_count=blog_posts_count,
        events_count=events_count,
        images_count=images_count,
        users_count=users_count,
        recent_actions=recent_actions,
    )


@bp.route('/blog')
@login_required
@admin_required
def blog():
    posts, total, source_label = _load_blog_posts_for_admin(limit=50)
    return render_template(
        "admin/blog/list.html",
        posts=posts,
        total=total,
        source_label=source_label,
    )


def _blog_form_values_from_post(post: dict) -> dict:
    return {
        "slug": post.get("slug") or "",
        "status": (post.get("status") or "") or "",
        "excerpt": post.get("excerpt") or "",
        "raw_tags": ", ".join(post.get("tags") or []),
        "cover_image_url": post.get("cover_image_url") or "",
        "seo_title": post.get("seo_title") or "",
        "meta_description": post.get("meta_description") or "",
        "og_title": post.get("og_title") or "",
        "og_description": post.get("og_description") or "",
        "final_posts": post.get("content_md") or "",
        "video_url": post.get("video_url") or "",
        "embed_url": post.get("embed_url") or "",
        "video_preview_image_url": post.get("video_poster_url") or "",
    }


@bp.route('/blog/<path:slug>', methods=['GET'])
@login_required
@admin_required
def blog_detail(slug: str):
    from app.config.blog_features import is_blog_admin_write_enabled
    from app.services.blog.store import get_post_by_slug
    from app.services.blog.suggest_card import seo_checklist_for_template

    post = get_post_by_slug(slug, prefer_sheets=True)
    if not post:
        abort(404)
    form_values = _blog_form_values_from_post(post)
    return render_template(
        "admin/blog/detail.html",
        post=post,
        write_enabled=is_blog_admin_write_enabled(),
        tags_str=form_values["raw_tags"],
        form_values=form_values,
        suggested_filled=False,
        seo_checklist=seo_checklist_for_template(form_values),
    )


@bp.route('/blog/<path:slug>/autofill', methods=['POST'])
@login_required
@admin_required
def blog_autofill(slug: str):
    """Подставить пустые SEO/теги/excerpt из текста поста (без записи в Sheets)."""
    from app.config.blog_features import is_blog_admin_write_enabled
    from app.services.blog.store import get_post_by_slug
    from app.services.blog.suggest_card import (
        build_card_suggestions,
        merge_empty_with_suggestions,
        seo_checklist_for_template,
    )

    if not is_blog_admin_write_enabled():
        flash("Запись отключена: BLOG_ADMIN_WRITE_ENABLED=0", "error")
        return redirect(url_for("admin.blog_detail", slug=slug))

    post = get_post_by_slug(slug, prefer_sheets=True)
    if not post:
        abort(404)

    current = _blog_form_values_from_post(post)
    suggestions = build_card_suggestions(post)
    form_values = merge_empty_with_suggestions(current, suggestions)
    form_values["status"] = current.get("status") or post.get("status") or "PUBLISHED"
    checklist = seo_checklist_for_template(form_values)
    flash(
        f"Пустые поля заполнены. SEO-оценка: {checklist['score']}/100 — "
        f"{checklist['label']}. Проверьте и сохраните.",
        "success",
    )
    return render_template(
        "admin/blog/detail.html",
        post=post,
        write_enabled=True,
        tags_str=form_values.get("raw_tags") or "",
        form_values=form_values,
        suggested_filled=True,
        seo_checklist=checklist,
    )


@bp.route('/blog/<path:slug>/save', methods=['POST'])
@login_required
@admin_required
def blog_save(slug: str):
    from app.config.blog_features import is_blog_admin_write_enabled
    from app.services.blog.admin_writeback import write_admin_fields
    from app.services.blog.store import get_post_by_slug
    from app.services.blog.suggest_card import (
        build_card_suggestions,
        merge_empty_with_suggestions,
        seo_checklist_for_template,
    )

    if not is_blog_admin_write_enabled():
        flash("Запись отключена: BLOG_ADMIN_WRITE_ENABLED=0", "error")
        return redirect(url_for("admin.blog_detail", slug=slug))

    post = get_post_by_slug(slug, prefer_sheets=True)
    if not post:
        abort(404)

    sheet_id = str(post.get("id") or "").strip()
    row_number = post.get("row_number")
    if not sheet_id or not row_number:
        flash(
            "Нельзя сохранить: нет id/row_number у строки (нужен Sheets primary).",
            "error",
        )
        return redirect(url_for("admin.blog_detail", slug=slug))

    raw_fields = {
        "excerpt": request.form.get("excerpt"),
        "cover_image_url": request.form.get("cover_image_url"),
        "raw_tags": request.form.get("raw_tags"),
        "seo_title": request.form.get("seo_title"),
        "meta_description": request.form.get("meta_description"),
        "og_title": request.form.get("og_title"),
        "og_description": request.form.get("og_description"),
        "slug": request.form.get("slug"),
    }
    fields = merge_empty_with_suggestions(raw_fields, build_card_suggestions(post))
    # Тело/видео не участвуют в autofill SEO — всегда из формы (B4.2).
    fields["final_posts"] = request.form.get("final_posts") if request.form.get("final_posts") is not None else (post.get("content_md") or "")
    fields["video_url"] = request.form.get("video_url") or ""
    fields["embed_url"] = request.form.get("embed_url") or ""
    fields["video_preview_image_url"] = request.form.get("video_preview_image_url") or ""

    status = (request.form.get("status") or "").strip() or None
    force_save = request.form.get("force_save") == "1"
    confirm_body = request.form.get("confirm_body_write") == "1"
    original_body = (post.get("content_md") or "").strip()
    new_body = (fields.get("final_posts") or "").strip()
    body_changed = new_body != original_body
    if body_changed and not confirm_body:
        flash(
            "Текст статьи изменён: отметьте «Подтверждаю запись final_posts в Sheets» "
            "(это перезапишет поле Parser).",
            "error",
        )
        form_values = {
            **fields,
            "status": status or post.get("status") or "",
        }
        checklist = seo_checklist_for_template({**fields, "status": status or ""})
        return render_template(
            "admin/blog/detail.html",
            post=post,
            write_enabled=True,
            tags_str=form_values.get("raw_tags") or "",
            form_values=form_values,
            suggested_filled=False,
            seo_checklist=checklist,
        )

    checklist = seo_checklist_for_template({**fields, "status": status or ""})

    if checklist["fails"] and not force_save:
        flash(
            f"SEO-чеклист: {checklist['fails']} критичных замечаний "
            f"(оценка {checklist['score']}/100). Исправьте поля или отметьте "
            f"«Сохранить несмотря на замечания».",
            "error",
        )
        form_values = {**fields, "status": status or post.get("status") or ""}
        return render_template(
            "admin/blog/detail.html",
            post=post,
            write_enabled=True,
            tags_str=form_values.get("raw_tags") or "",
            form_values=form_values,
            suggested_filled=False,
            seo_checklist=checklist,
        )

    ok, message, written = write_admin_fields(
        sheet_id=sheet_id,
        row_number=int(row_number),
        fields=fields,
        status=status,
    )
    if ok:
        flash(
            f"Сохранено в raw_feed: {', '.join(written)}. "
            f"SEO {checklist['score']}/100 ({checklist['label']}).",
            "success",
        )
        new_slug = (fields.get("slug") or slug).strip() or slug
        return redirect(url_for("admin.blog_detail", slug=new_slug))

    flash(f"Ошибка записи: {message}", "error")
    return redirect(url_for("admin.blog_detail", slug=slug))


@bp.route('/blog/<path:slug>/invalidate-cache', methods=['POST'])
@login_required
@admin_required
def blog_invalidate_cache(slug: str):
    from app.services.blog.store import invalidate_blog_sheets_cache

    invalidate_blog_sheets_cache()
    flash("Кэш блога (Sheets) сброшен.", "success")
    return redirect(url_for("admin.blog_detail", slug=slug))


@bp.route('/events')
@login_required
@admin_required
def events():
    try:
        rows = (
            CalendarEvent.query.order_by(CalendarEvent.start.desc().nullslast(), CalendarEvent.id.desc())
            .limit(100)
            .all()
        )
    except Exception as exc:
        current_app.logger.warning("admin_events_list_failed err=%s", exc)
        rows = []
    return render_template("admin/events/list.html", events=rows, total=len(rows))


@bp.route('/users')
@login_required
@admin_required
def users():
    try:
        rows = User.query.order_by(User.id.asc()).limit(200).all()
    except Exception as exc:
        current_app.logger.warning("admin_users_list_failed err=%s", exc)
        rows = []
    return render_template("admin/users/list.html", users=rows, total=len(rows))


@bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template(
        "admin/settings.html",
        flag_rows=_settings_flag_rows(),
        app_version=current_app.config.get("VERSION", "unknown"),
    )
