"""Register default tools for the Core AI Gateway."""
from __future__ import annotations

from typing import Any, Callable, Dict
import logging

from werkzeug.exceptions import BadRequest
from jsonschema.exceptions import ValidationError

from app.ai.core_gateway import ToolDefinition
from app.ai.tools_schema import get_schema_for, validate_tool_input

logger = logging.getLogger(__name__)


def _validated(tool_name: str, adapter: Callable[[Dict[str, Any]], Any], payload: Dict[str, Any] | None):
    try:
        validate_tool_input(tool_name, payload)
    except ValidationError as exc:
        raise BadRequest(f"Invalid payload for {tool_name}: {exc.message}")
    return adapter(payload or {})


def register_default_tools(app=None):
    """Attempt to register useful showcase + booking tools on the gateway instance."""

    try:
        from app.routes.ai_gateway_api import gateway
        from app.services.tools import get_available_slots as fetch_slots, book_slot
        from app.services.project_service import get_projects
        from app.services.faq_service import get_faq_answer as fetch_faq_answer
        from app.services.showcases import (
            get_showcase_itinerary as fetch_itinerary,
            get_challenge_leaderboard as fetch_leaderboard,
            join_challenge as join_showcase,
        )
    except Exception as exc:
        logger.debug('Could not import gateway dependencies: %s', exc)
        return

    # get_services
    def get_services_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            projects = get_projects()
            city = (data.get('city') or '').strip().lower()
            tags = {str(tag).strip().lower() for tag in data.get('tags') or []}
            if city:
                projects = [p for p in projects if str(p.get('city', '')).strip().lower() == city]
            if tags:
                projects = [p for p in projects if tags.issubset({str(t).strip().lower() for t in p.get('tags', [])})]
            return {'services': projects}

        return _validated('get_services', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='get_services', description='List available services/projects with optional filters', schema=get_schema_for('get_services')),
        get_services_tool,
    )

    # get_available_slots
    def get_slots_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            date = data.get('date')
            service_id = data.get('service_id')
            slots = fetch_slots(date)
            return {'service_id': service_id, 'date': date, 'slots': slots}

        return _validated('get_available_slots', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='get_available_slots', description='Get available slots for a service and date', schema=get_schema_for('get_available_slots')),
        get_slots_tool,
    )

    # create_booking
    def create_booking_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            slot = data.get('slot') or {}
            result = book_slot(slot.get('date'), slot.get('time'), data.get('name'), data.get('phone'))
            return {'service_id': data.get('service_id'), 'slot': slot, **result}

        return _validated('create_booking', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='create_booking', description='Create booking for a service with date, slot, name, phone', schema=get_schema_for('create_booking')),
        create_booking_tool,
    )

    # get_faq_answer
    def get_faq_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            return fetch_faq_answer(data.get('question'))

        return _validated('get_faq_answer', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='get_faq_answer', description='Answer frequently asked questions from riders', schema=get_schema_for('get_faq_answer')),
        get_faq_tool,
    )

    # Showcase-specific tools
    def get_itinerary_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            return fetch_itinerary(data['showcase_id'], data.get('date'))

        return _validated('get_showcase_itinerary', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='get_showcase_itinerary', description='Return Safari/Challenge itinerary', schema=get_schema_for('get_showcase_itinerary')),
        get_itinerary_tool,
    )

    def get_leaderboard_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            return fetch_leaderboard(data['showcase_id'], data.get('limit', 10))

        return _validated('get_challenge_leaderboard', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='get_challenge_leaderboard', description='Return challenge leaderboard data', schema=get_schema_for('get_challenge_leaderboard')),
        get_leaderboard_tool,
    )

    def join_challenge_tool(payload: Dict[str, Any]):
        def _adapter(data: Dict[str, Any]):
            return join_showcase(data['showcase_id'], data)

        return _validated('join_challenge', _adapter, payload)

    gateway.register_tool(
        ToolDefinition(name='join_challenge', description='Join Safari/Challenge waitlist or leaderboard', schema=get_schema_for('join_challenge')),
        join_challenge_tool,
    )

    logger.info('Default AI tools registered successfully with showcase extensions')
