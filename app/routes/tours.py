from flask import Blueprint, request, jsonify, current_app
from app.database.models import db, Tour, TourPackage
from datetime import datetime

tours_bp = Blueprint('tours', __name__)


def tour_to_dict(tour: Tour):
    return {
        'id': tour.id,
        'region': tour.region,
        'city': tour.city,
        'start_date': tour.start_date.isoformat() if tour.start_date else None,
        'end_date': tour.end_date.isoformat() if tour.end_date else None,
        'level': tour.level,
        'partner_club': tour.partner_club,
        'capacity': tour.capacity,
        'description': tour.description,
        'packages': [
            {
                'id': p.id,
                'name': p.name,
                'price_rub': p.price_rub,
                'available': p.available,
                'includes': p.includes
            } for p in tour.packages
        ]
    }


@tours_bp.route('/api/tours', methods=['GET'])
def list_tours():
    region = request.args.get('region')
    month = request.args.get('month')
    level = request.args.get('level')

    query = Tour.query
    if region:
        query = query.filter(Tour.region == region)
    if level:
        query = query.filter(Tour.level == level)
    if month:
        # month expected in YYYY-MM or YYYY-MM-DD, try to parse prefix
        try:
            parsed = datetime.fromisoformat(month)
            start_month = parsed.replace(day=1).date()
            # naive filter: tour start_date month equals
            query = query.filter(db.extract('year', Tour.start_date) == start_month.year,
                                 db.extract('month', Tour.start_date) == start_month.month)
        except Exception:
            pass

    items = query.order_by(Tour.start_date.asc()).limit(100).all()
    return jsonify(items=[tour_to_dict(t) for t in items])


@tours_bp.route('/api/tours/<int:tour_id>', methods=['GET'])
def get_tour(tour_id):
    tour = Tour.query.get_or_404(tour_id)
    return jsonify(tour_to_dict(tour))
