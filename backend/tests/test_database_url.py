from app.database.url import normalize_database_url


def test_normalizes_legacy_postgres_url_for_psycopg_3() -> None:
    assert normalize_database_url("postgres://user:pass@db/app") == (
        "postgresql+psycopg://user:pass@db/app"
    )


def test_normalizes_postgresql_url_for_psycopg_3() -> None:
    assert normalize_database_url("postgresql://user:pass@db/app?sslmode=require") == (
        "postgresql+psycopg://user:pass@db/app?sslmode=require"
    )


def test_preserves_explicit_dialect_and_sqlite_urls() -> None:
    explicit_url = "postgresql+psycopg://user:pass@db/app"
    assert normalize_database_url(explicit_url) == explicit_url
    assert normalize_database_url("sqlite:///./legacyguard.db") == "sqlite:///./legacyguard.db"
