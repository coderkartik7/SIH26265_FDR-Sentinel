import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import get_settings

settings = get_settings()

# If TESTING environment variable is set or DATABASE_URL has sqlite, use sqlite
if os.getenv("TESTING", "").lower() in ("true", "1"):
    db_url = os.getenv("TEST_DATABASE_URL", settings.TEST_DATABASE_URL)
else:
    db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)

if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
