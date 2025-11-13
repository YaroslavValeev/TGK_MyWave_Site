"""Register default tools for the Core AI Gateway.

This module registers small adapter functions that map tool calls to existing
service functions. It's safe to import in development and testing; any external
network calls are avoided because app config defaults disable Google services.
"""
from typing import Dict, Any
import logging

from app.ai.core_gateway import ToolDefinition

logger = logging.getLogger(__name__)


def register_default_tools(app=None):
    """Attempt to register a small set of useful tools on the gateway instance.

    This is intentionally defensive: imports are inside the function to avoid
    causing import-time failures when optional dependencies are missing.
    """
    try:
        # Lazy import to avoid import-time side effects
        from app.routes.ai_gateway_api import gateway
        from app.services.tools import get_available_slots, book_slot
        from app.services.project_service import get_projects

        # Tool: get_routes / get_services -> project listing
        def get_services_tool(payload: Dict[str, Any]):
            projects = get_projects()
            # allow optional filter by slug
            slug = payload.get('slug') if isinstance(payload, dict) else None
            if slug:
                projects = [p for p in projects if p.get('slug') == slug]
            return {'projects': projects}

        gateway.register_tool(
            ToolDefinition(name='get_services', description='List available services/projects'),
            get_services_tool,
        )

        # Tool: get_available_slots -> calls into app.services.tools
        def get_slots_tool(payload: Dict[str, Any]):
            date = payload.get('date') if isinstance(payload, dict) else None
            if not date:
                raise ValueError('date is required')
            slots = get_available_slots(date)
            return {'date': date, 'slots': slots}

        gateway.register_tool(
            ToolDefinition(name='get_available_slots', description='Get available slots for a date'),
            get_slots_tool,
        )

        # Tool: create_booking -> uses book_slot
        def create_booking_tool(payload: Dict[str, Any]):
            # expect {date, time, name, phone}
            date = payload.get('date')
            time = payload.get('time')
            name = payload.get('name')
            phone = payload.get('phone')
            if not all([date, time, name, phone]):
                raise ValueError('date,time,name,phone required')
            result = book_slot(date, time, name, phone)
            return result

        gateway.register_tool(
            ToolDefinition(name='create_booking', description='Create booking on sheets'),
            create_booking_tool,
        )

        logger.info('Default AI tools registered successfully')
    except Exception as e:
        logger.debug(f'Could not register default tools: {e}')
