"""Club adapter checks without importing Site's application or loading .env.

Run with --confcutdir=tests/isolated to exclude the full Site test bootstrap.
"""

import importlib.util
import json
from pathlib import Path

import pytest
from flask import Flask

SOURCE = Path(__file__).resolve().parents[2] / "app/config/club_config.py"
SPEC = importlib.util.spec_from_file_location("isolated_club_config", SOURCE)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)

SCHEMA = {
    "type": "object",
    "required": ["club"],
    "properties": {
        "club": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
    },
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ("CLUB_CONFIG_PATH", "CLUB_SCHEMA_PATH", "CLUB_CONFIG_VALIDATE"):
        monkeypatch.delenv(name, raising=False)


def write_club(tmp_path):
    path = tmp_path / "club.yaml"
    path.write_text("club:\n  name: Club B\nmodules:\n  booking_boat: true\n")
    return path


def application():
    app = Flask(__name__)
    adapter.load_club_config_into_app(app)
    adapter.register_club_module_guards(app)
    app.add_url_rule("/api/calendar/book", "booking", lambda: "ok", methods=["POST"])
    return app


@pytest.mark.parametrize("explicit", [True, False])
@pytest.mark.parametrize(
    "schema_case", ["unset", "missing", "invalid_json", "invalid_schema"]
)
def test_strict_validation_blocks_unverified_club(
    tmp_path, monkeypatch, explicit, schema_case
):
    club = write_club(tmp_path)
    if explicit:
        monkeypatch.setenv("CLUB_CONFIG_PATH", str(club))
    monkeypatch.setenv("CLUB_CONFIG_VALIDATE", "1")
    if schema_case != "unset":
        schema = tmp_path / "schema.json"
        monkeypatch.setenv("CLUB_SCHEMA_PATH", str(schema))
        if schema_case == "invalid_json":
            schema.write_text("{")
        elif schema_case == "invalid_schema":
            schema.write_text(json.dumps({"type": "not-a-json-schema-type"}))
    assert adapter.load_club_yaml(validate=True) is None
    app = application()
    assert app.config["CLUB_CONFIG_ERROR"] == "invalid_or_unreadable"
    assert all(enabled is False for enabled in app.config["CLUB"]["modules"].values())
    assert app.test_client().post("/api/calendar/book").status_code == 404


def test_valid_schema_allows_club_and_booking(tmp_path, monkeypatch):
    folder = tmp_path / "Клуб Б с пробелами"
    folder.mkdir()
    club = write_club(folder)
    schema = folder / "schema.json"
    schema.write_text(json.dumps(SCHEMA))
    monkeypatch.setenv("CLUB_CONFIG_PATH", str(club.relative_to(tmp_path)))
    monkeypatch.setenv("CLUB_SCHEMA_PATH", str(schema.relative_to(tmp_path)))
    monkeypatch.setenv("CLUB_CONFIG_VALIDATE", "1")
    app = application()
    assert app.config["CLUB"]["club"]["name"] == "Club B"
    assert "CLUB_CONFIG_ERROR" not in app.config
    assert app.test_client().post("/api/calendar/book").status_code == 200


def test_schema_rejects_invalid_club(tmp_path, monkeypatch):
    club = write_club(tmp_path)
    club.write_text("club:\n  name: 123\nmodules:\n  booking_boat: true\n")
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps(SCHEMA))
    monkeypatch.setenv("CLUB_SCHEMA_PATH", str(schema))
    monkeypatch.setenv("CLUB_CONFIG_VALIDATE", "1")
    app = application()
    assert app.config["CLUB_CONFIG_ERROR"] == "invalid_or_unreadable"
    assert app.test_client().post("/api/calendar/book").status_code == 404


def test_validation_opt_out_preserves_legacy_loading(tmp_path):
    write_club(tmp_path)
    assert adapter.load_club_yaml(validate=False)["club"]["name"] == "Club B"
    assert application().test_client().post("/api/calendar/book").status_code == 200


def test_no_club_config_preserves_default_site(monkeypatch):
    monkeypatch.setenv("CLUB_CONFIG_VALIDATE", "1")
    app = application()
    assert app.config["CLUB"] is None
    assert "CLUB_CONFIG_ERROR" not in app.config
    assert app.test_client().post("/api/calendar/book").status_code == 200
