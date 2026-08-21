from __future__ import annotations


def normalize_database_url(database_url: str) -> str:
    """Select psycopg 3 for PostgreSQL URLs while leaving other dialects intact."""
    if database_url.startswith("postgres://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgres://')}"
    if database_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{database_url.removeprefix('postgresql://')}"
    return database_url
