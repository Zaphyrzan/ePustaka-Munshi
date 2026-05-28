"""
Database connection pool utilities optimized for serverless environments.
Provides connection pool monitoring, retry logic, and health checks for Vercel/Supabase.
"""
from sqlalchemy import event, text
from sqlalchemy.pool import Pool, QueuePool
from sqlalchemy.exc import DBAPIError, OperationalError
import logging
import time
from functools import wraps
from typing import Optional, Callable, Any
import os

logger = logging.getLogger(__name__)


class ConnectionPoolMonitor:
    """
    Monitor database connection pool health and statistics.
    Useful for debugging connection exhaustion on serverless.
    """
    
    def __init__(self, db_engine):
        """
        Initialize pool monitor with SQLAlchemy engine.
        
        Args:
            db_engine: SQLAlchemy Engine instance
        """
        self.engine = db_engine
        self.stats = {
            'total_connections': 0,
            'connections_checked_in': 0,
            'connections_checked_out': 0,
            'connection_errors': 0,
            'last_error': None,
            'pool_overflow_count': 0,
        }
    
    def get_pool_stats(self) -> dict:
        """Get current connection pool statistics"""
        if not hasattr(self.engine.pool, 'checkedout'):
            return self.stats.copy()
        
        return {
            'total_connections': self.stats['total_connections'],
            'checked_out': len(self.engine.pool.checkedout()),
            'checked_in': self.engine.pool.size(),
            'connection_errors': self.stats['connection_errors'],
            'pool_overflow_count': self.stats['pool_overflow_count'],
            'last_error': self.stats['last_error'],
            'is_vercel': os.environ.get('VERCEL') is not None,
        }
    
    def log_pool_status(self):
        """Log current pool status to logger"""
        stats = self.get_pool_stats()
        msg = (
            f"Pool Status - "
            f"Checked Out: {stats.get('checked_out', '?')}, "
            f"Checked In: {stats.get('checked_in', '?')}, "
            f"Errors: {stats['connection_errors']}"
        )
        logger.info(msg)
    
    def track_connection_error(self, error: Exception):
        """Track connection errors for monitoring"""
        self.stats['connection_errors'] += 1
        self.stats['last_error'] = str(error)
        logger.warning(f"Connection pool error: {error}", exc_info=True)
    
    def track_pool_overflow(self):
        """Track pool overflow events"""
        self.stats['pool_overflow_count'] += 1
        logger.warning("Connection pool overflow - max_overflow limit reached")


def setup_connection_pool_listeners(db_engine, monitor: Optional[ConnectionPoolMonitor] = None):
    """
    Setup SQLAlchemy event listeners for connection pool monitoring and health checks.
    
    Args:
        db_engine: SQLAlchemy Engine instance
        monitor: Optional ConnectionPoolMonitor instance
    """
    if monitor is None:
        monitor = ConnectionPoolMonitor(db_engine)
    
    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Called when a new database connection is established"""
        monitor.stats['total_connections'] += 1
        logger.debug("Database connection established")
    
    @event.listens_for(Pool, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Called when connection is checked out from pool"""
        monitor.stats['connections_checked_out'] += 1
    
    @event.listens_for(Pool, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Called when connection is returned to pool"""
        monitor.stats['connections_checked_in'] += 1
    
    @event.listens_for(Pool, "detach")
    def receive_detach(dbapi_conn, connection_record):
        """Called when connection is detached from pool (connection invalid)"""
        logger.warning("Connection detached from pool - likely stale")
        monitor.track_connection_error("Connection detached - stale connection")
    
    @event.listens_for(Pool, "invalidate")
    def receive_invalidate(dbapi_conn, connection_record, exception):
        """Called when connection is invalidated"""
        logger.warning(f"Connection invalidated: {exception}")
        monitor.track_connection_error(exception)
    
    return monitor


def retry_on_db_error(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying database operations on transient connection errors.
    Useful for serverless where connections may timeout or be interrupted.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier (delay = backoff_factor ** attempt)
        on_retry: Optional callback called on retry(attempt_num, error)
    
    Usage:
        @retry_on_db_error(max_retries=3)
        def query_expensive_data():
            return db.session.query(Book).all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    last_error = e
                    
                    if attempt == max_retries - 1:
                        # Last attempt failed, raise error
                        logger.error(
                            f"Database operation failed after {max_retries} attempts: {e}",
                            exc_info=True
                        )
                        raise
                    
                    # Calculate backoff delay
                    delay = backoff_factor ** attempt
                    logger.warning(
                        f"Database operation attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    time.sleep(delay)
            
            # This shouldn't be reached, but just in case
            raise last_error
        
        return wrapper
    return decorator


def health_check_db(db_engine, timeout: float = 5.0) -> tuple[bool, str]:
    """
    Perform a simple health check on the database connection.
    Useful for monitoring and debugging.
    
    Args:
        db_engine: SQLAlchemy Engine instance
        timeout: Query timeout in seconds
    
    Returns:
        Tuple of (is_healthy, status_message)
    
    Usage:
        is_healthy, message = health_check_db(db.engine)
        if not is_healthy:
            logger.error(f"DB unhealthy: {message}")
    """
    try:
        # Simple ping query
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True, "Database connection healthy"
    except Exception as e:
        error_msg = f"Database health check failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def create_pool_aware_session(db_instance, monitor: Optional[ConnectionPoolMonitor] = None):
    """
    Create a database session factory with pool monitoring.
    
    Args:
        db_instance: Flask-SQLAlchemy db instance
        monitor: Optional ConnectionPoolMonitor instance
    
    Returns:
        Session factory with monitoring
    """
    if monitor is None:
        monitor = ConnectionPoolMonitor(db_instance.engine)
    
    original_session = db_instance.session
    
    # Add pool monitoring to session
    original_session.pool_monitor = monitor
    
    return original_session


class ServerlessPoolConfig:
    """
    Pre-configured connection pool settings optimized for serverless.
    Each configuration balances connection reuse with serverless isolation.
    """
    
    # Vercel/Lambda: Minimal pool, fail fast on exhaustion
    VERCEL = {
        'pool_size': 1,           # 1 connection per isolated function instance
        'max_overflow': 0,        # Fail immediately if pool exhausted
        'pool_pre_ping': True,    # Verify connections before use
        'pool_recycle': 3600,     # Recycle every hour (pooler timeout)
        'echo': False,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 5,
        }
    }
    
    # Development: More lenient pooling
    DEVELOPMENT = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'echo': False,
        'connect_args': {
            'connect_timeout': 30,
        }
    }
    
    # High-concurrency (future): More aggressive pooling
    HIGH_CONCURRENCY = {
        'pool_size': 20,
        'max_overflow': 40,
        'pool_pre_ping': True,
        'pool_recycle': 900,      # Recycle every 15 min
        'echo': False,
        'connect_args': {
            'connect_timeout': 15,
            'keepalives': 1,
            'keepalives_idle': 30,
        }
    }
    
    @staticmethod
    def get_config_for_environment() -> dict:
        """Auto-detect and return appropriate pool config for environment"""
        if os.environ.get('VERCEL'):
            return ServerlessPoolConfig.VERCEL.copy()
        elif os.environ.get('ENV') == 'production':
            return ServerlessPoolConfig.HIGH_CONCURRENCY.copy()
        else:
            return ServerlessPoolConfig.DEVELOPMENT.copy()


# Global monitor instance (optional, for app-level monitoring)
_pool_monitor: Optional[ConnectionPoolMonitor] = None


def get_pool_monitor() -> Optional[ConnectionPoolMonitor]:
    """Get the global pool monitor instance"""
    return _pool_monitor


def set_pool_monitor(monitor: ConnectionPoolMonitor):
    """Set the global pool monitor instance"""
    global _pool_monitor
    _pool_monitor = monitor
