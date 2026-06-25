"""P0 public routes: robots.txt, privacy, offer, PR54 legal consents."""

from flask import Blueprint, make_response, render_template

from app.services.project_applications import CONSENT_VERSION

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


@public_p0_bp.route("/legal/personal-data-consent", methods=["GET"], endpoint="legal_personal_data_consent")
def legal_personal_data_consent():
    return render_template("legal/personal-data-consent.html", consent_version=CONSENT_VERSION)


@public_p0_bp.route("/legal/media-consent", methods=["GET"], endpoint="legal_media_consent")
def legal_media_consent():
    return render_template("legal/media-consent.html", consent_version=CONSENT_VERSION)


@public_p0_bp.route("/legal/wake-challenge-consent", methods=["GET"], endpoint="legal_wake_challenge_consent")
def legal_wake_challenge_consent():
    return render_template("legal/wake-challenge-consent.html", consent_version=CONSENT_VERSION)
