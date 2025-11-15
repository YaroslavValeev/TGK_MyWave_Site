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

        # Tool: get_services -> project listing with optional filters
        def get_services_tool(payload: Dict[str, Any]):
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

        from app.ai.tools_schema import get_schema_for

        gateway.register_tool(
            ToolDefinition(name='get_services', description='List available services/projects with optional filters (city, tags)', schema=get_schema_for('get_services')),
            get_services_tool,
        )

        # Tool: get_available_slots -> calls into app.services.tools
        def get_slots_tool(payload: Dict[str, Any]):
            service_id = payload.get('service_id') if isinstance(payload, dict) else None
            date = payload.get('date') if isinstance(payload, dict) else None
            if not date:
                raise ValueError('date is required')
            if not service_id:
                raise ValueError('service_id is required')
            
            # For now, service_id is accepted but not used (future extension)
            slots = get_available_slots(date)
            return {'service_id': service_id, 'date': date, 'slots': slots}

        gateway.register_tool(
            ToolDefinition(name='get_available_slots', description='Get available slots for a service and date', schema=get_schema_for('get_available_slots')),
            get_slots_tool,
        )

        # Tool: create_booking -> uses book_slot
        def create_booking_tool(payload: Dict[str, Any]):
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

        logger.info('Default AI tools registered successfully')
    except Exception as e:
        logger.debug(f'Could not register default tools: {e}')
