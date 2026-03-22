import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    from app.db.session import engine
    from app.db.base import Base
    import app.models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created successfully.")


if __name__ == "__main__":
    asyncio.run(create_tables())
