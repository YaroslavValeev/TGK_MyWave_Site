"""Events-1: content_type classifier and normalized schema."""

from datetime import date

import pytest

from app.services.competitions.visibility import parse_iso_date
from app.services.events.classifier import (
    classify_competitions_ticker_row,
    classify_row,
    should_route_to_blog_vitrine,
)
from app.services.events.schema import (
    normalize_competitions_ticker_row,
    normalize_raw_feed_row,
)


class TestExplicitContentType:
    def test_explicit_competition(self):
        result = classify_row(
            {
                "content_type": "competition",
                "title": "IWWF Stage",
                "start_date": "2026-08-01",
                "location": "Orlando",
            }
        )
        assert result.content_type == "competition"
        assert result.needs_review is False
        assert "explicit_content_type" in result.reasons

    def test_explicit_invalid_falls_through_heuristic(self):
        result = classify_row(
            {
                "content_type": "unknown",
                "raw_title": "Чемпионат России по вейксерфингу",
                "start_date": "2026-07-01",
                "location": "Москва",
            }
        )
        assert result.content_type == "competition"


class TestHeuristicClassifier:
    def test_competition_keywords(self):
        result = classify_row(
            {
                "raw_title": "Чемпионат мира по вейксерфингу — регистрация открыта",
                "start_date": "2026-09-10",
                "location": "USA",
            }
        )
        assert result.content_type == "competition"
        assert result.confidence >= 0.55

    def test_camp_keywords(self):
        result = classify_row(
            {
                "title": "Летний кэмп MyWave Ruza",
                "start_date": "2026-07-15",
                "city": "Руза",
            }
        )
        assert result.content_type == "camp"

    def test_workshop_keywords(self):
        result = classify_row(
            {
                "title": "Мастер-класс по вейксерфингу для начинающих",
                "start_date": "2026-06-20",
                "location": "Зал",
            }
        )
        assert result.content_type == "workshop"

    def test_news_fallback(self):
        result = classify_row(
            {
                "title": "Обзор сезона: итоги и интервью с тренером",
                "status": "PUBLISHED",
            }
        )
        assert result.content_type == "news"

    def test_needs_review_missing_date_for_competition(self):
        result = classify_row({"raw_title": "Турнир по вейкборду"})
        assert result.content_type == "competition"
        assert result.needs_review is True
        assert result.track_status == "needs_review"
        assert "missing_start_date" in result.reasons


class TestCompetitionsTicker:
    def test_ticker_row_is_competition(self):
        result = classify_competitions_ticker_row(
            {
                "id": "evt-1",
                "status": "ACTIVE",
                "event_name": "WSWS Open",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "location": "Orlando",
                "country": "USA",
            }
        )
        assert result.content_type == "competition"
        assert result.track_status == "published"
        assert result.needs_review is False

    def test_ticker_missing_name_needs_review(self):
        result = classify_competitions_ticker_row(
            {"status": "ACTIVE", "start_date": "2026-10-01"}
        )
        assert result.needs_review is True
        assert result.track_status == "needs_review"


class TestNormalizedSchema:
    def test_normalize_raw_feed_row(self):
        classification = classify_row(
            {
                "id": "row-42",
                "title": "Лагерь Ruza",
                "start_date": "2026-07-01",
                "city": "Руза",
            }
        )
        item = normalize_raw_feed_row(
            {"id": "row-42", "title": "Лагерь Ruza", "start_date": "2026-07-01", "city": "Руза"},
            classification,
            start_date=parse_iso_date("2026-07-01"),
        )
        assert item.event_id == "row-42"
        assert item.content_type == "camp"
        assert item.start_date == date(2026, 7, 1)

    def test_normalize_ticker_row(self):
        classification = classify_competitions_ticker_row(
            {
                "id": "t1",
                "event_name": "IWWF",
                "start_date": "2026-08-01",
                "status": "ACTIVE",
            }
        )
        item = normalize_competitions_ticker_row(
            {"id": "t1", "event_name": "IWWF", "start_date": "2026-08-01"},
            classification,
            start_date=date(2026, 8, 1),
        )
        assert item.content_type == "competition"
        assert item.title == "IWWF"


class TestBlogVitrineHelper:
    def test_non_news_not_routed(self):
        result = classify_row(
            {
                "raw_title": "Чемпионат",
                "start_date": "2026-08-01",
                "location": "X",
            }
        )
        assert should_route_to_blog_vitrine(result) is False

    def test_news_can_route(self):
        result = classify_row(
            {"title": "Новости клуба", "status": "PUBLISHED", "text": "body"}
        )
        assert result.content_type == "news"
        assert should_route_to_blog_vitrine(result) is True

    def test_needs_review_never_routes(self):
        result = classify_row({"raw_title": "Турнир"})
        assert should_route_to_blog_vitrine(result) is False
