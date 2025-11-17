from __future__ import annotations

from typing import Any, Dict, List

from app.services.showcases import get_project_cards


def get_projects() -> List[Dict[str, Any]]:
    """Return normalized project cards for AI tools and legacy templates."""

    cards = get_project_cards()
    normalized = []
    for card in cards:
        normalized.append(
            {
                'slug': card['slug'],
                'title': card['name'],
                'description': card['summary'],
                'image': card.get('cover'),
                'detail': card.get('has_detail', False),
                'city': card.get('city'),
                'tags': card.get('tags', []),
                'level': card.get('level'),
                'price_from': card.get('price_from'),
            }
        )
    return normalized
