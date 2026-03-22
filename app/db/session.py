from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

_is_sqlite = "sqlite" in settings.DATABASE_URL

_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "echo": False,
}

if not _is_sqlite:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["connect_args"] = {"ssl": False}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
