"""Site adapter for Club Box club.yaml (P6)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from flask import Flask, abort, request

MODULE_KEYS = ("booking_boat", "shop", "blog", "reviews", "contacts")

SERVICE_ID_TO_MODULE: dict[str, str] = {
    "boat": "booking_boat",
}

# Path prefixes blocked when module is disabled (club.yaml modules section present).
# Keep longest/common prefixes; exact match and prefix+"/" are handled in the guard.
MODULE_ROUTE_PREFIXES: dict[str, tuple[str, ...]] = {
    "booking_boat": (
        "/book",
        "/booking",
        "/calendar",
        "/api/calendar",
        "/api/booking",
        "/api/bookings",
        "/services/book",
    ),
    "shop": ("/shop",),
    "blog": ("/blog", "/api/blog"),
    "reviews": ("/reviews",),
    "contacts": ("/contact", "/contacts"),
}


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _explicit_club_config_path_env() -> str:
    return (os.environ.get("CLUB_CONFIG_PATH") or "").strip()


def _club_config_path() -> Path | None:
    raw = _explicit_club_config_path_env() or "./club.yaml"
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path if path.is_file() else None


def _schema_path() -> Path | None:
    raw = (os.environ.get("CLUB_SCHEMA_PATH") or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path if path.is_file() else None


def _deny_all_modules_club() -> dict[str, Any]:
    """Fail-closed shell when club.yaml was required but could not be loaded."""
    return {"modules": {key: False for key in MODULE_KEYS}}


def load_club_yaml(*, validate: bool = False) -> dict[str, Any] | None:
    path = _club_config_path()
    if path is None:
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if validate:
        schema = _schema_path()
        if schema:
            try:
                import jsonschema

                schema_obj = json.loads(schema.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator(schema_obj).validate(data)
            except Exception:
                return None
    return data


def club_has_module_config(club: dict[str, Any] | None) -> bool:
    return bool(club and isinstance(club.get("modules"), dict))


def get_enabled_modules(club: dict[str, Any] | None) -> dict[str, bool] | None:
    """None = no filtering (MyWave default without club.yaml modules)."""
    if not club_has_module_config(club):
        return None
    mods = club.get("modules") or {}
    return {key: bool(mods.get(key, False)) for key in MODULE_KEYS}


def is_module_enabled(module: str, club: dict[str, Any] | None = None) -> bool:
    enabled = get_enabled_modules(club)
    if enabled is None:
        return True
    return bool(enabled.get(module, False))


def filter_services_config(services: list[dict[str, Any]], club: dict[str, Any] | None) -> list[dict[str, Any]]:
    enabled = get_enabled_modules(club)
    if enabled is None:
        return services
    out: list[dict[str, Any]] = []
    for item in services:
        sid = (item.get("service_id") or "").strip()
        mod = SERVICE_ID_TO_MODULE.get(sid)
        if mod is None:
            continue
        if enabled.get(mod):
            out.append(item)
    return out


def path_blocked_by_disabled_module(path: str, club: dict[str, Any] | None) -> bool:
    """True if request path should 404 because its module is disabled."""
    enabled = get_enabled_modules(club)
    if enabled is None:
        return False
    path = path or ""
    for module, prefixes in MODULE_ROUTE_PREFIXES.items():
        if enabled.get(module):
            continue
        for prefix in prefixes:
            if path == prefix or path.startswith(prefix + "/"):
                return True
    return False


def load_club_config_into_app(app: Flask) -> None:
    validate = _truthy_env("CLUB_CONFIG_VALIDATE")
    explicit = bool(_explicit_club_config_path_env())
    path = _club_config_path()

    if explicit and path is None:
        app.config["CLUB"] = _deny_all_modules_club()
        app.config["CLUB_CONFIG_ERROR"] = "missing_file"
        app.logger.error(
            "club_config_missing_file path=%s — fail-closed (all gated modules off)",
            _explicit_club_config_path_env(),
        )
        return

    club = load_club_yaml(validate=validate)
    if explicit and club is None:
        app.config["CLUB"] = _deny_all_modules_club()
        app.config["CLUB_CONFIG_ERROR"] = "invalid_or_unreadable"
        app.logger.error(
            "club_config_invalid path=%s — fail-closed (all gated modules off)",
            _explicit_club_config_path_env(),
        )
        return

    app.config["CLUB"] = club
    app.config.pop("CLUB_CONFIG_ERROR", None)


def register_club_module_guards(app: Flask) -> None:
    @app.before_request
    def _club_box_module_guard():
        club = app.config.get("CLUB")
        if path_blocked_by_disabled_module(request.path or "", club):
            abort(404)
        return None

    @app.context_processor
    def _inject_club_context():
        club = app.config.get("CLUB") or {}
        branding = club.get("branding") or {}
        return {
            "club_config": club,
            "club_modules": get_enabled_modules(club),
            "club_brand_name": branding.get("brand_name") or (club.get("club") or {}).get("name") or "",
        }
