from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import signal_settings

engine = create_async_engine(signal_settings.POSTGRES_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
