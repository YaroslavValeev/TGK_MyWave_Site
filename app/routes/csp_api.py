"""
API endpoint для сбора нарушений Content Security Policy.
Регистрируется в app/__init__.py вместе с recommendations_api.
"""

from flask import Blueprint, request, jsonify, current_app
from app.services.google_sheets_service import append_record
from flask_wtf.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

csp_bp = Blueprint('csp_bp', __name__)


@csp_bp.route('/csp-violations', methods=['POST'])
@csrf_exempt
def report_csp_violations():
    """Принимает и логирует нарушения Content Security Policy.
    
    Ожидает JSON с полями:
      - sessionId: UUID сессии браузера
      - url: URL страницы с нарушением
      - userAgent: User-Agent браузера
      - violations: [{ violatedDirective, blockedURI, sourceFile, ... }]
      - count: количество нарушений в этом отчёте
    
    Returns:
      { "ok": true, "logged": int }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('sessionId', 'unknown')
        page_url = data.get('url', 'unknown')
        user_agent = data.get('userAgent', 'unknown')
        violations = data.get('violations', [])
        
        if not violations:
            return jsonify({'ok': True, 'logged': 0})
        
        # Логируем каждое нарушение
        logged_count = 0
        for violation in violations:
            try:
                # Подготавливаем payload для Google Sheets
                payload = {
                    'event': 'csp_violation',
                    'context': 'security',
                    'user_key': session_id,
                    'rule_id': violation.get('violatedDirective', 'unknown'),
                    'item_id': '',
                    'type': 'csp',
                    'meta': {
                        'blockedURI': violation.get('blockedURI', ''),
                        'sourceFile': violation.get('sourceFile', ''),
                        'lineNumber': violation.get('lineNumber', 0),
                        'columnNumber': violation.get('columnNumber', 0),
                        'disposition': violation.get('disposition', ''),
                        'effectiveDirective': violation.get('effectiveDirective', ''),
                        'originalPolicy': violation.get('originalPolicy', '')[:200]  # Ограничиваем размер
                    },
                    'page_url': page_url[:500]  # Ограничиваем размер URL
                }
                
                # Преобразуем meta в JSON строку
                import json
                meta_json = json.dumps(payload['meta'])
                
                # Отправляем в Google Sheets (или в лог, если sheets недоступны)
                try:
                    from app.services.google_sheets_service import log_analytics_event
                    log_analytics_event(
                        payload={
                            'ts': int(__import__('time').time() * 1000),
                            'event': 'csp_violation',
                            'context': 'security',
                            'user_key': session_id,
                            'rule_id': violation.get('violatedDirective', ''),
                            'item_id': '',
                            'type': 'csp',
                            'meta_json': meta_json,
                            'ip': request.remote_addr,
                            'user_agent': user_agent[:500]
                        },
                        spreadsheet_id=None,  # Используем конфиг приложения
                        worksheet_name='csp_violations'
                    )
                except Exception as e:
                    logger.warning(f'Failed to log CSP violation to Sheets: {e}')
                    # Просто логируем в файл логов как фолбэк
                    logger.warning(f'CSP Violation from {session_id}: {violation}')
                
                logged_count += 1
            except Exception as e:
                logger.error(f'Error logging individual CSP violation: {e}')
        
        return jsonify({'ok': True, 'logged': logged_count})
    
    except Exception as e:
        logger.error(f'Error in CSP violations endpoint: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500
