"""
deps.py

FastAPI dependency injectors for database sessions and the event bus.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_bus() -> EventBus:
    from main import bus
    return bus
