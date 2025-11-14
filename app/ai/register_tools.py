"""Register default tools for the Core AI Gateway.

This module registers small adapter functions that map tool calls to existing
service functions. It's safe to import in development and testing; any external
network calls are avoided because app config defaults disable Google services.
"""
from typing import Dict, Any, Callable
import logging

from werkzeug.exceptions import BadRequest
from jsonschema.exceptions import ValidationError

from app.ai.core_gateway import ToolDefinition
from app.ai.tools_schema import get_schema_for, validate_tool_input

logger = logging.getLogger(__name__)


def register_default_tools(app=None):
    """Attempt to register a small set of useful tools on the gateway instance.

    This is intentionally defensive: imports are inside the function to avoid
    causing import-time failures when optional dependencies are missing.
    """
    try:
        # Lazy import to avoid import-time side effects
        from app.routes.ai_gateway_api import gateway
        from app.services.tools import get_available_slots as fetch_slots, book_slot
        from app.services.project_service import get_projects
        from app.services.faq_service import get_faq_answer as fetch_faq_answer

        def _validated(tool_name: str, adapter: Callable[[Dict[str, Any]], Any], payload: Dict[str, Any] | None):
            try:
                validate_tool_input(tool_name, payload)
            except ValidationError as exc:
                raise BadRequest(f"Invalid payload for {tool_name}: {exc.message}")
            return adapter(payload)

        # Tool: get_routes / get_services -> project listing
        def get_services_tool(payload: Dict[str, Any]):
            def _adapter(data: Dict[str, Any]):
                projects = get_projects()
                if not isinstance(data, dict):
                    return {'projects': projects}
                city = data.get('city')
                tags = data.get('tags') or []
                if city:
                    city_lower = str(city).strip().lower()
                    projects = [p for p in projects if str(p.get('city', '')).strip().lower() == city_lower]
                tag_set = {str(tag).strip().lower() for tag in tags if isinstance(tag, str)}
                if tag_set:
                    filtered = []
                    for project in projects:
                        project_tags = {str(t).strip().lower() for t in project.get('tags', [])}
                        if tag_set.issubset(project_tags):
                            filtered.append(project)
                    projects = filtered
                return {'projects': projects}

            return _validated('get_services', _adapter, payload)

        gateway.register_tool(
            ToolDefinition(name='get_services', description='List available services/projects', schema=get_schema_for('get_services')),
            get_services_tool,
        )

        # Tool: get_available_slots -> calls into app.services.tools
        def get_slots_tool(payload: Dict[str, Any]):
            def _adapter(data: Dict[str, Any]):
                date = data.get('date')
                service_id = data.get('service_id')
                slots = fetch_slots(date)
                return {'service_id': service_id, 'date': date, 'slots': slots}

            return _validated('get_available_slots', _adapter, payload)

        gateway.register_tool(
            ToolDefinition(name='get_available_slots', description='Get available slots for a date', schema=get_schema_for('get_available_slots')),
            get_slots_tool,
        )

        # Tool: create_booking -> uses book_slot
        def create_booking_tool(payload: Dict[str, Any]):
            def _adapter(data: Dict[str, Any]):
                slot = data.get('slot') or {}
                result = book_slot(slot.get('date'), slot.get('time'), data.get('name'), data.get('phone'))
                return {
                    'service_id': data.get('service_id'),
                    'slot': slot,
                    **result,
                }

            return _validated('create_booking', _adapter, payload)

        def get_faq_tool(payload: Dict[str, Any]):
            def _adapter(data: Dict[str, Any]):
                return fetch_faq_answer(data.get('question'))

            return _validated('get_faq_answer', _adapter, payload)

        gateway.register_tool(
            ToolDefinition(name='create_booking', description='Create booking on sheets', schema=get_schema_for('create_booking')),
            create_booking_tool,
        )

        gateway.register_tool(
            ToolDefinition(name='get_faq_answer', description='Answer frequently asked questions from riders', schema=get_schema_for('get_faq_answer')),
            get_faq_tool,
        )

        logger.info('Default AI tools registered successfully')
    except Exception as e:
        logger.debug(f'Could not register default tools: {e}')
