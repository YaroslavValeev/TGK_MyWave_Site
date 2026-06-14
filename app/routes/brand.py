"""Public brand assets (logo package download)."""

from __future__ import annotations

from flask import Blueprint, abort, send_file

from app.modules.logger import get_logger
from app.services.brand.logo_package import build_logo_package_zip

logger = get_logger(__name__)

brand_bp = Blueprint("brand", __name__)

LOGO_ZIP_NAME = "MyWave_logo_package.zip"


@brand_bp.get("/downloads/mywave-logo-package.zip")
def logo_package_download():
    try:
        payload = build_logo_package_zip()
    except FileNotFoundError:
        logger.warning("logo_package_download_missing_files")
        abort(404)
    except Exception as exc:
        logger.warning("logo_package_download_failed err=%s", exc)
        abort(500)

    return send_file(
        payload,
        mimetype="application/zip",
        as_attachment=True,
        download_name=LOGO_ZIP_NAME,
        max_age=3600,
    )
