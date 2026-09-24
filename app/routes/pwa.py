"""PWA: manifest + service worker for mobile home-screen install."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, send_from_directory, url_for

from app.services.pwa_manifest import build_pwa_manifest

pwa_bp = Blueprint("pwa", __name__)


@pwa_bp.route("/manifest.webmanifest")
def web_manifest():
    club = current_app.config.get("CLUB")
    icon_url = url_for("static", filename="pwa/icon-512.png", _external=True)
    manifest = build_pwa_manifest(club=club, static_icon_url=icon_url)
    resp = jsonify(manifest)
    resp.mimetype = "application/manifest+json"
    return resp


@pwa_bp.route("/sw.js")
def service_worker():
    return send_from_directory(
        current_app.static_folder,
        "pwa/sw.js",
        mimetype="application/javascript",
        max_age=3600,
    )
