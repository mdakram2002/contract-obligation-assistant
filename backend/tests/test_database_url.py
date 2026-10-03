import pytest

from app.database_url import normalize_async_database_url


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgres://user:password@db.example.test:5432/contracts",
            "postgresql+asyncpg://user:password@db.example.test:5432/contracts",
        ),
        (
            "postgresql://user:password@db.example.test:5432/contracts",
            "postgresql+asyncpg://user:password@db.example.test:5432/contracts",
        ),
        (
            "postgresql+psycopg2://user:password@db.example.test:5432/contracts",
            "postgresql+asyncpg://user:password@db.example.test:5432/contracts",
        ),
        (
            "postgresql+asyncpg://user:password@db.example.test:5432/contracts",
            "postgresql+asyncpg://user:password@db.example.test:5432/contracts",
        ),
        (
            "sqlite+aiosqlite:///:memory:",
            "sqlite+aiosqlite:///:memory:",
        ),
    ],
)
def test_normalize_async_database_url(database_url: str, expected: str) -> None:
    assert normalize_async_database_url(database_url) == expected
