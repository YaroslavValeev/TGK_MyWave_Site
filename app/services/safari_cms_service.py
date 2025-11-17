"""
Safari CMS Content Management Service

Управляет контентом для WakeSurfSafari из Google Sheets.
Синхронизирует маршруты, описания, цены и другой контент в БД.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database.models import db, Document, Tag
# Import Google helper lazily inside methods to avoid import-time
# dependency issues when tests run without Google config.

logger = logging.getLogger(__name__)

# Константы для синхронизации
SAFARI_SHEET_NAME = 'Safari_Content'
SAFARI_COLLECTION_NAME = 'safari'


class SafariCMSService:
    """Сервис для управления Safari контентом из Google Sheets."""

    @staticmethod
    def sync_routes() -> Dict[str, Any]:
        """
        Синхронизирует маршруты Safari из Google Sheets в БД.
        
        Ожидается лист 'Safari_Routes' с колонками:
        - route_id: уникальный идентификатор маршрута
        - name: название маршрута
        - description: описание маршрута
        - price: цена в рублях
        - duration_days: количество дней
        - difficulty_level: уровень сложности (beginner, intermediate, advanced)
        - capacity: вместимость участников
        - start_dates: доступные даты начала (JSON или CSV)
        - highlights: ключевые моменты (JSON или CSV)
        
        Returns:
            Dict с информацией о синхронизации (count, errors)
        """
        try:
            # Import lazily so tests that don't configure Google services don't fail at import-time
            from app.services.google import get_gsheet

            ws = get_gsheet().open('MyWave_Parser_News').worksheet('Safari_Routes')
        except Exception as e:
            logger.error(f"Failed to get Safari_Routes sheet: {e}")
            return {'success': False, 'error': str(e), 'count': 0}

        try:
            rows = ws.get_all_records()
        except Exception as e:
            logger.error(f"Failed to read Safari_Routes: {e}")
            return {'success': False, 'error': str(e), 'count': 0}

        synced = 0
        errors = []

        for row in rows:
            try:
                route_id = str(row.get('route_id', '')).strip()
                if not route_id or route_id.lower() == 'route_id':
                    continue  # пропускаем заголовок

                # Создаём или обновляем документ для маршрута
                doc = Document.query.filter_by(
                    title=route_id,
                ).first()

                if not doc:
                    doc = Document(
                        title=route_id,
                        content=row.get('description', ''),
                        meta={
                            'collection': SAFARI_COLLECTION_NAME,
                            'type': 'route',
                            'route_id': route_id,
                            'name': row.get('name', ''),
                            'price': int(row.get('price', 0)) if row.get('price') else 0,
                            'duration_days': int(row.get('duration_days', 0)) if row.get(
                                'duration_days') else 0,
                            'difficulty_level': row.get('difficulty_level', 'intermediate'),
                            'capacity': int(row.get('capacity', 0)) if row.get('capacity') else 0,
                            'highlights': row.get('highlights', ''),
                            'synced_at': datetime.utcnow().isoformat()
                        }
                    )
                else:
                    # Обновляем существующий документ
                    doc.content = row.get('description', '')
                    doc.meta = {
                        'collection': SAFARI_COLLECTION_NAME,
                        'type': 'route',
                        'route_id': route_id,
                        'name': row.get('name', ''),
                        'price': int(row.get('price', 0)) if row.get('price') else 0,
                        'duration_days': int(row.get('duration_days', 0)) if row.get(
                            'duration_days') else 0,
                        'difficulty_level': row.get('difficulty_level', 'intermediate'),
                        'capacity': int(row.get('capacity', 0)) if row.get('capacity') else 0,
                        'highlights': row.get('highlights', ''),
                        'synced_at': datetime.utcnow().isoformat()
                    }

                db.session.add(doc)
                synced += 1

            except Exception as e:
                logger.error(f"Error syncing route {row.get('route_id', 'unknown')}: {e}")
                errors.append(str(e))

        try:
            db.session.commit()
            logger.info(f"Safari routes synced: {synced} routes")
            return {
                'success': True,
                'count': synced,
                'errors': errors
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing Safari routes: {e}")
            return {
                'success': False,
                'error': str(e),
                'count': synced,
                'errors': errors + [str(e)]
            }

    @staticmethod
    def sync_faq() -> Dict[str, Any]:
        """
        Синхронизирует FAQ для Safari из Google Sheets в БД.
        
        Ожидается лист 'Safari_FAQ' с колонками:
        - question: вопрос
        - answer: ответ
        - category: категория (preparation, health, booking, rules и т.д.)
        - order: порядок отображения
        
        Returns:
            Dict с информацией о синхронизации
        """
        try:
            from app.services.google import get_gsheet

            ws = get_gsheet().open('MyWave_Parser_News').worksheet('Safari_FAQ')
        except Exception as e:
            logger.error(f"Failed to get Safari_FAQ sheet: {e}")
            return {'success': False, 'error': str(e), 'count': 0}

        try:
            rows = ws.get_all_records()
        except Exception as e:
            logger.error(f"Failed to read Safari_FAQ: {e}")
            return {'success': False, 'error': str(e), 'count': 0}

        synced = 0
        errors = []

        for row in rows:
            try:
                question = str(row.get('question', '')).strip()
                if not question or question.lower() == 'question':
                    continue

                # Ключ для поиска
                doc_key = f"safari_faq_{row.get('category', 'general')}_{synced}"

                doc = Document.query.filter_by(
                    title=question,
                ).first()

                if not doc:
                    doc = Document(
                        title=question,
                        content=row.get('answer', ''),
                        meta={
                            'collection': SAFARI_COLLECTION_NAME,
                            'type': 'faq',
                            'category': row.get('category', 'general'),
                            'order': int(row.get('order', 0)) if row.get('order') else 0,
                            'synced_at': datetime.utcnow().isoformat()
                        }
                    )
                else:
                    doc.content = row.get('answer', '')
                    doc.meta = {
                        'collection': SAFARI_COLLECTION_NAME,
                        'type': 'faq',
                        'category': row.get('category', 'general'),
                        'order': int(row.get('order', 0)) if row.get('order') else 0,
                        'synced_at': datetime.utcnow().isoformat()
                    }

                db.session.add(doc)
                synced += 1

            except Exception as e:
                logger.error(f"Error syncing FAQ {row.get('question', 'unknown')}: {e}")
                errors.append(str(e))

        try:
            db.session.commit()
            logger.info(f"Safari FAQ synced: {synced} items")
            return {
                'success': True,
                'count': synced,
                'errors': errors
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing Safari FAQ: {e}")
            return {
                'success': False,
                'error': str(e),
                'count': synced,
                'errors': errors + [str(e)]
            }

    @staticmethod
    def get_routes() -> List[Dict[str, Any]]:
        """
        Получает все синхронизированные маршруты Safari.
        
        Returns:
            Список маршрутов с метаданными
        """
        # Query all documents and filter in Python since JSON contains can be unreliable
        docs = Document.query.all()

        routes = []
        for doc in docs:
            if doc.meta and doc.meta.get('type') == 'route' and doc.meta.get('collection') == SAFARI_COLLECTION_NAME:
                route = {
                    'id': doc.id,
                    'route_id': doc.meta.get('route_id'),
                    'name': doc.meta.get('name', doc.title),
                    'description': doc.content,
                    'price': doc.meta.get('price', 0),
                    'duration_days': doc.meta.get('duration_days', 0),
                    'difficulty_level': doc.meta.get('difficulty_level', 'intermediate'),
                    'capacity': doc.meta.get('capacity', 0),
                    'highlights': doc.meta.get('highlights', ''),
                }
                routes.append(route)

        return sorted(routes, key=lambda x: x.get('name', ''))

    @staticmethod
    def get_faq(category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получает FAQ для Safari, опционально фильтруя по категории.
        
        Args:
            category: опциональная категория для фильтрации
            
        Returns:
            Список вопросов и ответов
        """
        # Query all documents and filter in Python since JSON contains can be unreliable
        docs = Document.query.all()

        faq_items = []
        for doc in docs:
            if doc.meta and doc.meta.get('type') == 'faq' and doc.meta.get('collection') == SAFARI_COLLECTION_NAME:
                if category and doc.meta.get('category') != category:
                    continue

                item = {
                    'id': doc.id,
                    'question': doc.title,
                    'answer': doc.content,
                    'category': doc.meta.get('category', 'general'),
                    'order': doc.meta.get('order', 0),
                }
                faq_items.append(item)

        return sorted(faq_items, key=lambda x: x.get('order', 0))

    @staticmethod
    def sync_all() -> Dict[str, Any]:
        """
        Выполняет полную синхронизацию всего Safari контента.
        
        Returns:
            Dict с результатами синхронизации всех коллекций
        """
        logger.info("Starting Safari CMS full sync...")

        results = {
            'routes': SafariCMSService.sync_routes(),
            'faq': SafariCMSService.sync_faq(),
            'timestamp': datetime.utcnow().isoformat(),
        }

        total_success = results['routes'].get('success', False) and results['faq'].get('success',
                                                                                          False)
        total_synced = results['routes'].get('count', 0) + results['faq'].get('count', 0)

        results['success'] = total_success
        results['total_synced'] = total_synced

        logger.info(f"Safari CMS sync complete: {total_synced} items")

        return results
