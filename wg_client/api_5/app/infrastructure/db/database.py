"""Database connection and session management"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from app.config import config


class Database:
    """Database connection manager"""
    
    def __init__(self):
        db_config = config.get_db_config()
        self.engine = create_engine(
            db_config.dsn,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,  # Set to True for SQL debugging
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session (context manager)"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """Get database session (direct, for FastAPI dependency)"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()


# Singleton instance
db = Database()


# FastAPI dependency
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session"""
    session = db.get_session_direct()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


