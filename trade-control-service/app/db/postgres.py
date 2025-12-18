from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import control_settings

# 1. Создаем асинхронный движок
engine = create_async_engine(control_settings.POSTGRES_URL, echo=False)

# 2. Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# 3. Базовый класс для моделей
Base = declarative_base()
