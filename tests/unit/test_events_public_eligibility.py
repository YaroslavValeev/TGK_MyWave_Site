"""Events-3 public eligibility tests."""

from datetime import date

from app.services.events.classifier import classify_competitions_ticker_row, classify_row
from app.services.events.public_eligibility import is_public_eligible
from app.services.events.schema import normalize_competitions_ticker_row, normalize_raw_feed_row


def _published_competition_item():
    row = {
        "id": "t-pub-001",
        "event_name": "IWWF Open",
        "start_date": "2026-09-01",
        "status": "ACTIVE",
        "location": "Orlando",
    }
    clf = classify_competitions_ticker_row(row)
    return normalize_competitions_ticker_row(row, clf, start_date=date(2026, 9, 1))


def _needs_review_item():
    row = {
        "id": "c-review",
        "raw_title": "Турнир без даты",
        "location": "Москва",
    }
    clf = classify_row(row)
    return normalize_raw_feed_row(row, clf)


class TestPublicEligibility:
    def test_published_competition_eligible(self):
        assert is_public_eligible(_published_competition_item()) is True

    def test_needs_review_not_eligible(self):
        assert is_public_eligible(_needs_review_item()) is False

    def test_parsed_status_not_eligible(self):
        item = _published_competition_item()
        item.track_status = "parsed"
        item.classification.track_status = "parsed"
        assert is_public_eligible(item) is False

    def test_needs_review_track_status_not_eligible(self):
        item = _published_competition_item()
        item.track_status = "needs_review"
        item.classification.needs_review = True
        assert is_public_eligible(item) is False

    def test_missing_title_not_eligible(self):
        item = _published_competition_item()
        item.title = ""
        assert is_public_eligible(item) is False

    def test_competition_without_date_not_eligible(self):
        item = _published_competition_item()
        item.start_date = None
        assert is_public_eligible(item) is False
