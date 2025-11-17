"""Reusable schema.org builders for showcase listings."""
from __future__ import annotations

from typing import Iterable, Mapping, Any

from flask import url_for


def _normalize_tags(tags: Iterable[str] | None) -> list[str]:
    return [str(tag).strip() for tag in tags or [] if str(tag).strip()]


def build_item_list(showcases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return ItemList description for a showcase collection."""
    elements = []
    for idx, showcase in enumerate(showcases, start=1):
        slug = showcase.get('slug') or showcase.get('id') or f"showcase-{idx}"
        url = showcase.get('absolute_url') or showcase.get('url') or url_for('projects_page', _external=True)
        elements.append({'@type': 'ListItem', 'position': idx, 'url': url, 'name': showcase.get('name')})
    return {'@type': 'ItemList', 'itemListElement': elements}


def build_showcase_schema(showcase: Mapping[str, Any]) -> dict[str, Any]:
    schema_type = showcase.get('schema_type') or showcase.get('@type') or 'Event'
    cover = showcase.get('cover') or showcase.get('cover_image')
    gallery = showcase.get('gallery') or []
    images = []
    if cover:
        images.append(url_for('static', filename=cover, _external=True))
    for img in gallery:
        images.append(url_for('static', filename=img, _external=True))
    additional_properties = []
    if showcase.get('tags'):
        additional_properties.append({'@type': 'PropertyValue', 'name': 'tags', 'value': ', '.join(_normalize_tags(showcase.get('tags')))} )
    if showcase.get('level'):
        additional_properties.append({'@type': 'PropertyValue', 'name': 'level', 'value': showcase['level']})
    if showcase.get('price_from'):
        additional_properties.append({'@type': 'PropertyValue', 'name': 'priceFrom', 'value': showcase['price_from']})
    if showcase.get('capacity'):
        additional_properties.append({'@type': 'PropertyValue', 'name': 'capacity', 'value': showcase['capacity']})
    location = None
    if showcase.get('city'):
        location = {'@type': 'Place', 'name': showcase['city'], 'address': f"{showcase.get('city')}, {showcase.get('country', '')}".strip(', ')}
    schema = {
        '@type': schema_type,
        'name': showcase.get('name'),
        'description': showcase.get('description') or showcase.get('summary'),
        'startDate': showcase.get('start_date'),
        'endDate': showcase.get('end_date'),
        'eventStatus': showcase.get('eventStatus') or 'https://schema.org/EventScheduled',
        'eventAttendanceMode': showcase.get('eventAttendanceMode') or 'https://schema.org/OfflineEventAttendanceMode',
        'url': showcase.get('absolute_url') or showcase.get('url'),
        'identifier': showcase.get('slug') or showcase.get('id'),
    }
    if images:
        schema['image'] = images
    if location:
        schema['location'] = location
    if additional_properties:
        schema['additionalProperty'] = additional_properties
    return schema


def build_showcase_graph(showcases: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not showcases:
        return {}
    return {'@context': 'https://schema.org', '@graph': [build_item_list(showcases), *[build_showcase_schema(sc) for sc in showcases]]}


def build_event_list(showcases: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [build_showcase_schema(sc) for sc in showcases]
