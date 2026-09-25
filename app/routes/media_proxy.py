"""GET /media/ext?u=<url> — внешняя обложка с нашего домена (кэш на диске)."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, redirect, request, send_file

from app.services.media_proxy import fetch_and_cache, find_cached, is_proxyable_url

media_proxy_bp = Blueprint("media_proxy", __name__)

_CACHE_MAX_AGE = 7 * 24 * 60 * 60


@media_proxy_bp.get("/media/ext")
def external_image():
    url = (request.args.get("u") or "").strip()
    if not is_proxyable_url(url):
        abort(400)
    path = find_cached(url, current_app.static_folder) or fetch_and_cache(url, current_app.static_folder)
    if not path:
        # Не хуже прежнего: браузер попробует загрузить оригинал сам.
        return redirect(url, code=302)
    return send_file(path, max_age=_CACHE_MAX_AGE, conditional=True)
