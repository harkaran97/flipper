from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

engine = create_async_engine(settings.database_url, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from app.models.base import Base
    # Import all models so they are registered with Base.metadata
    import app.models.listing  # noqa: F401
    import app.models.vehicle  # noqa: F401
    import app.models.fault  # noqa: F401
    import app.models.repair_estimate  # noqa: F401
    import app.models.market_value  # noqa: F401
    import app.models.opportunity  # noqa: F401
    import app.models.common_problem  # noqa: F401
    import app.models.car  # noqa: F401
    import app.models.cars_common_problems  # noqa: F401
    import app.models.exterior_condition  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
