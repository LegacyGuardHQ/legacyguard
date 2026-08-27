from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.url import normalize_database_url

SQLALCHEMY_DATABASE_URL = normalize_database_url(settings.database_url)

engine_kwargs = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL == "sqlite:///:memory:":
        engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def begin_serialized_write(db: Session) -> None:
    """Start a write transaction that serializes SQLite quota checks and writes."""
    if db.get_bind().dialect.name == "sqlite":
        # API dependencies may have already performed read queries. End that
        # deferred transaction before requesting SQLite's database write lock.
        db.rollback()
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def init_db() -> None:
    from app.models import audit_log, session, user, user_security_settings  # noqa: F401

    Base.metadata.create_all(bind=engine)
