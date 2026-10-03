from sqlalchemy.engine import make_url


def normalize_async_database_url(database_url: str) -> str:
    """Use asyncpg for PostgreSQL URLs consumed by SQLAlchemy async engines."""
    url = make_url(database_url)
    if url.get_backend_name() in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+asyncpg").render_as_string(
            hide_password=False
        )
    return database_url
