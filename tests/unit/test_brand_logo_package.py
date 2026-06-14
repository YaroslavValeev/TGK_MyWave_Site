"""Brand logo package download tests."""

from app.services.brand.logo_package import build_logo_package_zip, iter_logo_package_files


def test_logo_package_has_files(app):
    with app.app_context():
        files = list(iter_logo_package_files())
    assert len(files) >= 5
    names = [arc for _, arc in files]
    assert any("MyWave_logo_turquoise.svg" in n for n in names)
    assert any(n.endswith("README.md") for n in names)


def test_logo_package_zip_download(client):
    rv = client.get("/downloads/mywave-logo-package.zip")
    assert rv.status_code == 200
    assert rv.mimetype == "application/zip"
    assert b"PK" in rv.data[:4]
    assert len(rv.data) > 1000
