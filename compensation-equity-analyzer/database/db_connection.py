"""
Database Connection and Session Management
Supports MySQL with automatic graceful fallback to SQLite.
"""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

logger = logging.getLogger("db_connection")

Base = declarative_base()

def get_engine():
    # If MySQL is explicitly enabled and available, attempt connection
    if settings.USE_MYSQL:
        try:
            mysql_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
            engine = create_engine(
                mysql_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=settings.DEBUG
            )
            # Test connection
            with engine.connect() as conn:
                pass
            logger.info("Connected to MySQL database successfully.")
            return engine
        except Exception as e:
            logger.warning(f"MySQL unavailable ({e}). Falling back to SQLite.")

    # SQLite connection (compatible fallback)
    sqlite_url = f"sqlite:///{settings.SQLITE_PATH.as_posix()}"
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    logger.info(f"Using SQLite database at {settings.SQLITE_PATH}")
    return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables defined in models."""
    import models # ensure models are imported
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
