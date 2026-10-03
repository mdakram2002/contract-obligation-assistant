import asyncio
from app.database import engine, Base
from app.models import *  # Import all models to register them with Base


async def init_db():
    """Initialize the database with all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
