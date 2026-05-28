"""P0 public routes: robots.txt, privacy, offer."""

from flask import Blueprint, make_response, render_template

public_p0_bp = Blueprint("public_p0", __name__)


@public_p0_bp.route("/robots.txt", methods=["GET"])
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Sitemap: https://mywavewake.ru/sitemap.xml\n"
    )
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp


@public_p0_bp.route("/privacy", methods=["GET"], endpoint="privacy_page")
def privacy_page():
    return render_template("legal/privacy.html")


@public_p0_bp.route("/offer", methods=["GET"], endpoint="offer_page")
def offer_page():
    return render_template("legal/offer.html")
