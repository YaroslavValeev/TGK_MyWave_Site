"""Routes for WakeSurfSafari booking and information pages."""
from flask import Blueprint, render_template, jsonify, request
import logging

safari_bp = Blueprint('safari', __name__, url_prefix='/wakesurf-safari')
logger = logging.getLogger(__name__)


@safari_bp.route('/', methods=['GET'])
def safari_main():
    """Main WakeSurfSafari page with description and booking form."""
    return render_template('wakesurf_safari.html')


@safari_bp.route('/booking-success', methods=['GET'])
def booking_success():
    """Booking success confirmation page."""
    booking_id = request.args.get('id')
    return render_template('safari_booking_success.html', booking_id=booking_id)
