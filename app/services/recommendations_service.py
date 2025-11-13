import time
import hashlib
import logging
from datetime import datetime
from flask import current_app
from app.database.models import BlogPost, Image, CalendarEvent

logger = logging.getLogger(__name__)

# Простая in-memory кэширующая структура: key -> (ts, value)
_CACHE = {}

# Метрики для отслеживания эффективности кэша
_CACHE_HITS = 0
_CACHE_MISSES = 0

def _cache_get(key):
    global _CACHE_HITS, _CACHE_MISSES
    entry = _CACHE.get(key)
    if not entry:
        _CACHE_MISSES += 1
        return None
    ts, value = entry
    ttl = current_app.config.get('RECO_CACHE_TTL', 300)
    if time.time() - ts > ttl:
        try:
            del _CACHE[key]
        except KeyError:
            pass
        _CACHE_MISSES += 1
        return None
    _CACHE_HITS += 1
    return value

def _cache_set(key, value):
    _CACHE[key] = (time.time(), value)

def _ab_group(user_key):
    try:
        size = int(current_app.config.get('AB_CONTROL_GROUP_SIZE', 2))
        if not user_key:
            return 0
        h = hashlib.sha256(user_key.encode('utf-8')).hexdigest()
        return int(h, 16) % max(1, size)
    except Exception:
        return 0


def recommend(context: str = 'index', user_key: str = None, city: str = None, slug: str = None, limit: int = 4):
    """Возвращает до `limit` рекомендованных элементов для данного контекста.

    Элементы берём из нескольких источников в порядке приоритета: изображения группы 'services',
    свежие посты блога, предстоящие события. Результат кэшируется в памяти на RECO_CACHE_TTL.
    A/B сплит управляется по user_key и конфигу AB_CONTROL_GROUP_SIZE.
    """
    key = f"reco:{context}:{user_key}:{city}:{slug}:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    group = _ab_group(user_key)
    results = []

    try:
        # 1) Services (images grouped as 'services')
        try:
            services_q = Image.query.filter(Image.group == 'services').order_by(Image.order.asc()).limit(10).all()
            for img in services_q:
                results.append({
                    'id': f'image:{img.id}',
                    'title': img.title or img.filename,
                    'slug': '',
                    'type': 'service',
                    'image': img.url,
                    'rule_id': 'services_group'
                })
        except Exception:
            logger.debug('No services images found or DB unavailable')

        # 2) Recent blog posts
        try:
            posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(10).all()
            for p in posts:
                results.append({
                    'id': f'post:{p.id}',
                    'title': p.title,
                    'slug': p.slug,
                    'type': 'post',
                    'image': p.image.url if getattr(p, 'image', None) else '',
                    'rule_id': 'recent_posts'
                })
        except Exception:
            logger.debug('No posts found or DB unavailable')

        # 3) Upcoming events
        try:
            events = CalendarEvent.query.order_by(CalendarEvent.created_at.desc()).limit(10).all()
            for e in events:
                results.append({
                    'id': f'event:{e.id}',
                    'title': e.summary or 'Event',
                    'slug': '',
                    'type': 'event',
                    'image': '',
                    'rule_id': 'upcoming_events'
                })
        except Exception:
            logger.debug('No events found or DB unavailable')

        # Simple de-duplication by id preserving order
        seen = set()
        deduped = []
        for item in results:
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            deduped.append(item)

        # Optionally apply A/B experiment: group 1 receives only posts+events, group 0 receives full mix
        if group == 1:
            filtered = [i for i in deduped if i['type'] in ('post', 'event')]
        else:
            filtered = deduped

        final = filtered[:limit]
        _cache_set(key, final)
        return final
    except Exception as e:
        logger.exception(f'Failed to compute recommendations: {e}')
        return []


def get_cache_stats():
    """Возвращает статистику работы кэша рекомендаций.
    
    Returns:
        dict: {
            'hits': int,
            'misses': int,
            'hit_rate': float (от 0 до 100),
            'cache_size': int,
            'ttl_seconds': int
        }
    """
    global _CACHE_HITS, _CACHE_MISSES
    total = _CACHE_HITS + _CACHE_MISSES
    hit_rate = (_CACHE_HITS / total * 100) if total > 0 else 0
    ttl = current_app.config.get('RECO_CACHE_TTL', 300)
    
    return {
        'hits': _CACHE_HITS,
        'misses': _CACHE_MISSES,
        'hit_rate': round(hit_rate, 2),
        'cache_size': len(_CACHE),
        'ttl_seconds': ttl,
        'total_requests': total
    }


def reset_cache_stats():
    """Сбрасывает счётчики метрик кэша."""
    global _CACHE_HITS, _CACHE_MISSES
    _CACHE_HITS = 0
    _CACHE_MISSES = 0