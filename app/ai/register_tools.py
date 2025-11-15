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

        # Tool: get_services -> project listing with optional filters
        def get_services_tool(payload: Dict[str, Any]):
<<<<<<< HEAD
            projects = get_projects()
            city = payload.get('city') if isinstance(payload, dict) else None
            tags = payload.get('tags') if isinstance(payload, dict) else None
            
            # Filter by city (if implemented in project metadata)
            if city:
                # For now, city filtering is not implemented in project_service
                # but structure is ready for future extension
                pass
            
            # Filter by tags
            if tags and isinstance(tags, list):
                filtered = []
                for p in projects:
                    project_tags = p.get('tags', [])
                    if any(tag in project_tags for tag in tags):
                        filtered.append(p)
                projects = filtered
            
            return {'services': projects}
=======
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
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d

            return _validated('get_services', _adapter, payload)

        gateway.register_tool(
            ToolDefinition(name='get_services', description='List available services/projects with optional filters (city, tags)', schema=get_schema_for('get_services')),
            get_services_tool,
        )

        # Tool: get_available_slots -> calls into app.services.tools
        def get_slots_tool(payload: Dict[str, Any]):
<<<<<<< HEAD
            service_id = payload.get('service_id') if isinstance(payload, dict) else None
            date = payload.get('date') if isinstance(payload, dict) else None
            if not date:
                raise ValueError('date is required')
            if not service_id:
                raise ValueError('service_id is required')
            
            # For now, service_id is accepted but not used (future extension)
            slots = get_available_slots(date)
            return {'service_id': service_id, 'date': date, 'slots': slots}
=======
            def _adapter(data: Dict[str, Any]):
                date = data.get('date')
                service_id = data.get('service_id')
                slots = fetch_slots(date)
                return {'service_id': service_id, 'date': date, 'slots': slots}

            return _validated('get_available_slots', _adapter, payload)
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d

        gateway.register_tool(
            ToolDefinition(name='get_available_slots', description='Get available slots for a service and date', schema=get_schema_for('get_available_slots')),
            get_slots_tool,
        )

        # Tool: create_booking -> uses book_slot
        def create_booking_tool(payload: Dict[str, Any]):
<<<<<<< HEAD
            # expect {service_id, date, slot, name, phone, email?}
            service_id = payload.get('service_id')
            date = payload.get('date')
            slot = payload.get('slot')
            name = payload.get('name')
            phone = payload.get('phone')
            email = payload.get('email')
            
            if not all([service_id, date, slot, name, phone]):
                raise ValueError('service_id,date,slot,name,phone required')
            
            # For now, service_id is accepted but not used (future extension)
            # slot is used as time
            result = book_slot(date, slot, name, phone)
            
            # Add service_id and email to result if provided
            if email:
                result['email'] = email
            result['service_id'] = service_id
            
            return result
=======
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
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d

        gateway.register_tool(
            ToolDefinition(name='create_booking', description='Create booking for a service with date, slot, name, phone', schema=get_schema_for('create_booking')),
            create_booking_tool,
        )
        
        # Tool: get_faq_answer -> search FAQ knowledge base
        def get_faq_answer_tool(payload: Dict[str, Any]):
            question = payload.get('question') if isinstance(payload, dict) else None
            if not question:
                raise ValueError('question is required')
            
            # Try to find answer in static FAQ or knowledge base
            try:
                import os
                import json
                from flask import current_app
                
                # Try static FAQ file first
                faq_path = os.path.join(current_app.root_path, '..', 'static', 'data', 'faq.json')
                if os.path.exists(faq_path):
                    with open(faq_path, 'r', encoding='utf-8') as f:
                        faq_data = json.load(f)
                        faq_list = faq_data.get('faq', faq_data) if isinstance(faq_data, dict) else faq_data
                        
                        # Simple keyword matching
                        question_lower = question.lower()
                        for item in faq_list:
                            item_question = str(item.get('script_id') or item.get('question', '')).lower()
                            item_answer = str(item.get('script_name') or item.get('answer', ''))
                            if question_lower in item_question or any(word in item_question for word in question_lower.split() if len(word) > 3):
                                return {'question': question, 'answer': item_answer, 'source': 'static_faq'}
                
                # Fallback to knowledge base if no match
                try:
                    from app.routes.api import get_knowledge
                    # This would require refactoring get_knowledge to accept question and search
                    # For now, return a generic response
                    return {'question': question, 'answer': 'Для получения более подробной информации обратитесь к нашему FAQ разделу или свяжитесь с нами.', 'source': 'fallback'}
                except Exception:
                    pass
                
                return {'question': question, 'answer': 'К сожалению, я не нашел точного ответа на ваш вопрос. Пожалуйста, уточните вопрос или свяжитесь с нами напрямую.', 'source': 'not_found'}
            except Exception as e:
                logger.warning(f'Error in get_faq_answer: {e}')
                return {'question': question, 'answer': 'Произошла ошибка при поиске ответа. Попробуйте позже.', 'source': 'error'}

        gateway.register_tool(
            ToolDefinition(name='get_faq_answer', description='Search FAQ and knowledge base for answer to a question', schema=get_schema_for('get_faq_answer')),
            get_faq_answer_tool,
        )

        gateway.register_tool(
            ToolDefinition(name='get_faq_answer', description='Answer frequently asked questions from riders', schema=get_schema_for('get_faq_answer')),
            get_faq_tool,
        )

        logger.info('Default AI tools registered successfully')
    except Exception as e:
        logger.debug(f'Could not register default tools: {e}')
