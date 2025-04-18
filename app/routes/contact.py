from flask import Blueprint, render_template

contact_bp = Blueprint('contact', __name__, template_folder='../templates')

@contact_bp.route("/contact")
def contact():
    return render_template("contact.html")
    