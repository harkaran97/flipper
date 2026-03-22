import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure the backend directory is on the path so models can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.base import Base  # noqa: E402
import app.models.listing  # noqa: F401, E402
import app.models.vehicle  # noqa: F401, E402
import app.models.fault  # noqa: F401, E402
import app.models.repair_estimate  # noqa: F401, E402
import app.models.market_value  # noqa: F401, E402
import app.models.opportunity  # noqa: F401, E402
import app.models.common_problem  # noqa: F401, E402
import app.models.car  # noqa: F401, E402
import app.models.cars_common_problems  # noqa: F401, E402
import app.models.exterior_condition  # noqa: F401, E402
import app.models.fault_part  # noqa: F401, E402
import app.models.parts_search_result  # noqa: F401, E402
import app.models.user_settings  # noqa: F401, E402
import app.models.parts_price_cache  # noqa: F401, E402
import app.models.linkup_market_value_cache  # noqa: F401, E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable if set
database_url = os.environ.get("DATABASE_URL", "")
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
