import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def init_models(retries: int = 15, delay: float = 2.0) -> None:
    from app import models  # noqa: F401  (register models on Base.metadata)

    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema is ready")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Database not ready (attempt %s/%s): %s", attempt, retries, exc)
            await asyncio.sleep(delay)
    raise RuntimeError("Could not connect to the database after several retries")
