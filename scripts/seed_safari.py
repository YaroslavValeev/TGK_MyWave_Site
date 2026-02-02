"""Seed script: create sample participant and safari booking for local testing."""

from app.database.models import db, Participant, SafariBooking
from app import create_app

app = create_app("development")

with app.app_context():
    # Create sample participant
    p = Participant.query.filter_by(email="alice@example.com").first()
    if not p:
        p = Participant(
            name="Alice",
            email="alice@example.com",
            phone="+79123456789",
            level="intermediate",
        )
        db.session.add(p)
        db.session.commit()
        print("Participant created:", p.id)
    else:
        print("Participant exists:", p.id)

    # Create sample booking
    b = SafariBooking.query.filter_by(participant_id=p.id).first()
    if not b:
        from datetime import date

        b = SafariBooking(
            participant_id=p.id,
            status="confirmed",
            start_date=date.today(),
            days=3,
            message="Seed booking",
        )
        db.session.add(b)
        db.session.commit()
        print("SafariBooking created:", b.id)
    else:
        print("SafariBooking exists:", b.id)
