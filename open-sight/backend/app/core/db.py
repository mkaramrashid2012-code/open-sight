"""Enterprise-grade database connection management with pooling and resilience."""
import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class DatabaseManager:
    """Manages database connections with pooling, retries, and health checks."""
    
    def __init__(self):
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[scoped_session] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            return
        
        logger.info("Initializing database connection pool...")
        
        try:
            # Create engine with enterprise-grade connection pooling
            self._engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,  # Enable connection health checks
                pool_recycle=3600,   # Recycle connections after 1 hour
                pool_timeout=30,     # Timeout for getting connection from pool
                echo=settings.debug,  # SQL logging in debug mode
                future=True,
            )
            
            # Configure connection settings
            @event.listens_for(self._engine, "connect")
            def set_postgresql_settings(dbapi_connection, connection_record):
                """Set connection-level configurations for PostgreSQL."""
                if 'postgresql' in settings.database_url:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("SET TIME ZONE 'UTC'")
                    cursor.close()
                    logger.debug("PostgreSQL timezone set to UTC")
            
            # Create session factory
            self._session_factory = scoped_session(
                sessionmaker(
                    bind=self._engine,
                    autocommit=False,
                    autoflush=False,
                    expire_on_commit=False,
                )
            )
            
            # Verify connection
            self._verify_connection()
            
            self._initialized = True
            logger.info(f"Database initialized with pool_size={settings.db_pool_size}, max_overflow={settings.db_max_overflow}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _verify_connection(self) -> None:
        """Verify database connectivity."""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection verified")
        except Exception as e:
            logger.error(f"Database connection verification failed: {e}")
            raise
    
    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        if not self._initialized:
            self.initialize()
        return self._engine
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self._initialized:
            self.initialize()
        return self._session_factory()
    
    def get_session_factory(self):
        """Get the session factory for dependency injection."""
        if not self._initialized:
            self.initialize()
        return self._session_factory
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def health_check(self) -> dict:
        """Perform database health check."""
        if not self._initialized:
            return {"status": "not_initialized", "healthy": False}
        
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Get pool statistics
                pool_status = {
                    "pool_size": self._engine.pool.size(),
                    "checked_in": self._engine.pool.checkedin(),
                    "checked_out": self._engine.pool.checkedout(),
                    "overflow": self._engine.pool.overflow(),
                }
                
                return {
                    "status": "healthy",
                    "healthy": True,
                    "pool": pool_status,
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
            }
    
    def close(self) -> None:
        """Close all database connections."""
        if self._session_factory:
            self._session_factory.remove()
        if self._engine:
            self._engine.dispose()
        self._initialized = False
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI endpoints - yields database sessions."""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


def init_database() -> DatabaseManager:
    """Initialize the database manager."""
    db_manager.initialize()
    return db_manager


def get_engine() -> Engine:
    """Get the database engine."""
    return db_manager.engine


# Legacy compatibility
SessionLocal = lambda: db_manager.get_session()
