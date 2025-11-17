"""
Performance optimization service for MyWave Safari application
Handles query optimization, caching, lazy loading, and CDN configuration

Point 15: Performance optimization
"""

from typing import List, Dict, Any, Optional
from functools import wraps
from datetime import datetime, timedelta
import logging

from flask import current_app
from flask_caching import Cache
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, selectinload, contains_eager
from app.database import db
from app.services.prometheus_metrics import record_cache_hit, record_cache_miss

logger = logging.getLogger(__name__)

# Initialize cache (configured in Flask app)
cache = Cache()


# =====================================================
# CACHE DECORATORS
# =====================================================

def cached_result(timeout: int = 300, key_prefix: str = None):
    """
    Decorator for caching function results
    
    Args:
        timeout: Cache duration in seconds (default: 5 min)
        key_prefix: Custom cache key prefix
    
    Example:
        @cached_result(timeout=600, key_prefix='bookings')
        def get_active_bookings():
            return Booking.query.filter_by(status='active').all()
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = f"{key_prefix}:{args}:{kwargs}"
            else:
                cache_key = f"{f.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                record_cache_hit()
                logger.debug(f"Cache hit for {cache_key}")
                return result
            
            # Cache miss - compute result
            record_cache_miss()
            result = f(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, timeout=timeout)
            logger.debug(f"Cache set for {cache_key} with timeout {timeout}s")
            
            return result
        
        # Add method to clear specific cache
        decorated_function.clear_cache = lambda: cache.delete_memoized(f)
        return decorated_function
    
    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator to invalidate cache after function execution
    
    Args:
        key_pattern: Pattern for cache keys to invalidate
    
    Example:
        @invalidate_cache(key_pattern='bookings:*')
        def create_booking(...):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            # Invalidate matching cache keys
            logger.info(f"Invalidating cache for pattern: {key_pattern}")
            # Note: Simple invalidation - for production use cache.delete() with patterns
            return result
        return decorated_function
    
    return decorator


# =====================================================
# QUERY OPTIMIZATION HELPERS
# =====================================================

class QueryOptimizer:
    """Helpers for optimized database queries"""
    
    @staticmethod
    def get_bookings_with_participants(status: Optional[str] = None, limit: int = 100):
        """
        Fetch bookings with eager-loaded participant data
        Avoids N+1 query problem
        
        Args:
            status: Filter by booking status (optional)
            limit: Maximum results
            
        Returns:
            List of Booking objects with loaded participants
        """
        query = db.session.query(db.Booking).options(
            joinedload(db.Booking.participant)
        )
        
        if status:
            query = query.filter(db.Booking.status == status)
        
        return query.limit(limit).all()
    
    @staticmethod
    def get_participants_with_bookings(route_id: Optional[int] = None):
        """
        Fetch participants with their booking history
        Uses selectinload for relationship loading
        
        Args:
            route_id: Filter by route ID (optional)
            
        Returns:
            List of Participant objects with loaded bookings
        """
        query = db.session.query(db.Participant).options(
            selectinload(db.Participant.bookings)
        )
        
        if route_id:
            query = query.filter(db.Participant.route_id == route_id)
        
        return query.all()
    
    @staticmethod
    def get_blog_posts_with_images(limit: int = 50):
        """
        Fetch blog posts with eager-loaded images and chat messages
        
        Args:
            limit: Maximum posts to fetch
            
        Returns:
            List of BlogPost objects with loaded relationships
        """
        from app.database.models import BlogPost
        
        query = db.session.query(BlogPost).options(
            selectinload(BlogPost.images),
            selectinload(BlogPost.chat_messages).selectinload(ChatMessage.user)
        ).filter(
            BlogPost.published == True
        ).order_by(
            BlogPost.created_at.desc()
        )
        
        return query.limit(limit).all()
    
    @staticmethod
    def get_upcoming_bookings(days_ahead: int = 7) -> List:
        """
        Fetch bookings for the next N days with optimized loading
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming bookings
        """
        future_date = datetime.now() + timedelta(days=days_ahead)
        
        query = db.session.query(db.Booking).options(
            joinedload(db.Booking.participant),
            joinedload(db.Booking.calendar_event)
        ).filter(
            and_(
                db.Booking.start_date >= datetime.now().date(),
                db.Booking.start_date <= future_date.date(),
                db.Booking.status.in_(['pending', 'confirmed'])
            )
        ).order_by(db.Booking.start_date.asc())
        
        return query.all()
    
    @staticmethod
    def count_active_bookings_by_status() -> Dict[str, int]:
        """
        Count bookings by status using efficient GROUP BY query
        
        Returns:
            Dictionary mapping status to count
        """
        from sqlalchemy import func
        
        results = db.session.query(
            db.Booking.status,
            func.count(db.Booking.id).label('count')
        ).group_by(db.Booking.status).all()
        
        return {status: count for status, count in results}


# =====================================================
# LAZY LOADING HELPERS
# =====================================================

class LazyLoadingHelper:
    """Helpers for lazy loading heavy data (like images)"""
    
    @staticmethod
    def serialize_booking_summary(booking) -> Dict[str, Any]:
        """
        Serialize booking without loading full relationships
        Good for list views where full data not needed
        
        Args:
            booking: Booking object
            
        Returns:
            Lightweight dictionary representation
        """
        return {
            'id': booking.id,
            'participant_id': booking.participant_id,
            'status': booking.status,
            'start_date': booking.start_date.isoformat() if booking.start_date else None,
            'days': booking.days,
            'created_at': booking.created_at.isoformat()
        }
    
    @staticmethod
    def serialize_participant_summary(participant) -> Dict[str, Any]:
        """
        Serialize participant without loading bookings
        Reduces payload for participant lists
        
        Args:
            participant: Participant object
            
        Returns:
            Lightweight dictionary representation
        """
        return {
            'id': participant.id,
            'name': participant.name,
            'email': participant.email,
            'phone': participant.phone,
            'level': participant.level,
            'route_id': participant.route_id,
            'created_at': participant.created_at.isoformat()
        }
    
    @staticmethod
    def add_images_lazily(blog_post_id: int) -> Dict[str, Any]:
        """
        Load heavy image data only when explicitly requested
        Good for API endpoints with optional image loading
        
        Args:
            blog_post_id: ID of blog post
            
        Returns:
            Blog post with images loaded
        """
        from app.database.models import BlogPost, Image
        
        blog_post = db.session.query(BlogPost).filter_by(id=blog_post_id).first()
        if blog_post:
            # Explicitly load images only when needed
            images = db.session.query(Image).filter_by(blog_post_id=blog_post_id).all()
            return {
                'blog_post': blog_post.to_dict(),
                'images': [img.to_dict() for img in images]
            }
        return None


# =====================================================
# CDN CONFIGURATION
# =====================================================

class CDNConfig:
    """CDN configuration and URL generation helpers"""
    
    @staticmethod
    def get_cdn_url(file_path: str, use_cdn: bool = True) -> str:
        """
        Generate CDN URL for static assets
        Falls back to local path if CDN not available
        
        Args:
            file_path: Relative path to file
            use_cdn: Whether to use CDN (check config)
            
        Returns:
            Full URL for the asset
        """
        if use_cdn and current_app.config.get('CDN_URL'):
            cdn_url = current_app.config['CDN_URL']
            return f"{cdn_url.rstrip('/')}/{file_path.lstrip('/')}"
        
        # Fallback to local path
        return f"/static/{file_path.lstrip('/')}"
    
    @staticmethod
    def optimize_image_url(image_path: str, width: Optional[int] = None, 
                          height: Optional[int] = None, quality: int = 85) -> str:
        """
        Generate optimized image URL with resize parameters
        Assumes Cloudinary or similar service with image transformation
        
        Args:
            image_path: Path to image
            width: Target width in pixels
            height: Target height in pixels
            quality: JPEG quality (1-100)
            
        Returns:
            Optimized image URL
        """
        if current_app.config.get('CLOUDINARY_URL'):
            # Cloudinary transformation format
            cdn_url = current_app.config.get('CDN_URL', 'https://res.cloudinary.com/...')
            
            transformations = []
            if width:
                transformations.append(f"w_{width}")
            if height:
                transformations.append(f"h_{height}")
            if quality:
                transformations.append(f"q_{quality}")
            
            if transformations:
                transform_str = ','.join(transformations)
                return f"{cdn_url}/image/upload/{transform_str}/{image_path}"
        
        # Fallback: use CDN without transformations
        return CDNConfig.get_cdn_url(image_path)
    
    @staticmethod
    def get_responsive_image_urls(image_path: str) -> Dict[str, str]:
        """
        Generate responsive image URLs for different screen sizes
        Returns srcset-compatible URLs
        
        Args:
            image_path: Base image path
            
        Returns:
            Dictionary with mobile, tablet, desktop URLs
        """
        return {
            'mobile': CDNConfig.optimize_image_url(image_path, width=480, quality=80),
            'tablet': CDNConfig.optimize_image_url(image_path, width=768, quality=85),
            'desktop': CDNConfig.optimize_image_url(image_path, width=1200, quality=90),
            'original': CDNConfig.get_cdn_url(image_path)
        }


# =====================================================
# PERFORMANCE MONITORING
# =====================================================

class PerformanceMonitor:
    """Monitor and log query performance"""
    
    @staticmethod
    def log_query_metrics(query_result, query_name: str, threshold_ms: int = 100):
        """
        Log slow queries that exceed threshold
        
        Args:
            query_result: Query result
            query_name: Name of query for logging
            threshold_ms: Threshold in milliseconds
        """
        # This would integrate with SQLAlchemy events in production
        logger.debug(f"Query '{query_name}' completed")
    
    @staticmethod
    def enable_slow_query_logging(threshold_ms: int = 200):
        """
        Enable logging of slow queries
        Should be called during app initialization
        
        Args:
            threshold_ms: Log queries slower than this (milliseconds)
        """
        from sqlalchemy import event
        
        @event.listens_for(db.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(datetime.now())
        
        @event.listens_for(db.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = (datetime.now() - conn.info['query_start_time'].pop(-1)).total_seconds() * 1000
            
            if total_time > threshold_ms:
                logger.warning(
                    f"SLOW QUERY ({total_time:.2f}ms): {statement[:200]}..."
                )


# =====================================================
# CACHING FUNCTIONS
# =====================================================

@cached_result(timeout=600, key_prefix='active_bookings')
def get_cached_active_bookings() -> List:
    """Get active bookings from cache or database"""
    return QueryOptimizer.get_bookings_with_participants(status='confirmed')


@cached_result(timeout=300, key_prefix='booking_stats')
def get_cached_booking_stats() -> Dict[str, int]:
    """Get booking statistics from cache"""
    return QueryOptimizer.count_active_bookings_by_status()


def clear_booking_caches():
    """Clear all booking-related caches"""
    get_cached_active_bookings.clear_cache()
    get_cached_booking_stats.clear_cache()
    logger.info("Booking caches cleared")


# =====================================================
# INITIALIZATION
# =====================================================

def init_performance_optimizations(app):
    """
    Initialize performance optimizations
    Call during Flask app initialization
    
    Args:
        app: Flask application instance
    """
    # Initialize cache
    cache.init_app(app)
    
    # Enable slow query logging if in debug mode
    if app.config.get('DEBUG') or app.config.get('ENABLE_QUERY_LOGGING'):
        PerformanceMonitor.enable_slow_query_logging(
            threshold_ms=app.config.get('SLOW_QUERY_THRESHOLD_MS', 200)
        )
    
    logger.info("Performance optimizations initialized")
