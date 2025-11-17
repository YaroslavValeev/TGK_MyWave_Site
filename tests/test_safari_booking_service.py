import pytest
from datetime import date

from app import create_app
from app.database.models import db, Participant, SafariBooking
from app.services import safari_booking_service


@pytest.fixture(scope='module')
def test_app():
    app = create_app('testing')
    with app.app_context():
        # Drop and recreate tables in test DB to ensure clean state
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_upsert_participant_and_create_booking(test_app):
    payload = {
        'name': 'Test User',
        'email': 'testuser@example.com',
        'phone': '+70000000000',
        'level': 'beginner',
        'startDate': date.today().isoformat(),
        'days': 2,
        'message': 'Looking forward'
    }

    booking = safari_booking_service.create_booking(payload)
    assert booking is not None
    assert booking.id is not None
    assert booking.status in ('pending', 'confirmed', 'created')

    # Participant should exist
    p = Participant.query.filter_by(email=payload['email']).first()
    assert p is not None
    assert p.name == payload['name']


def test_get_booking(test_app):
    # create a booking first
    payload = {
        'name': 'Getter',
        'email': 'getter@example.com',
        'phone': '+70000000001',
        'level': 'intermediate',
        'startDate': date.today().isoformat(),
        'days': 1,
        'message': ''
    }
    b = safari_booking_service.create_booking(payload)
    fetched = safari_booking_service.get_booking(b.id)
    assert fetched is not None
    assert fetched.id == b.id
    assert fetched.participant_id == b.participant_id


def test_update_booking(test_app):
    payload = {
        'name': 'Updater',
        'email': 'updater@example.com',
        'phone': '+70000000002',
        'level': 'advanced',
        'startDate': date.today().isoformat(),
        'days': 4,
        'message': 'Initial'
    }
    b = safari_booking_service.create_booking(payload)
    update = {'status': 'confirmed', 'message': 'Updated message'}
    updated = safari_booking_service.update_booking(b.id, update)
    assert updated is not None
    assert updated.status == 'confirmed'
    assert updated.message == 'Updated message'
