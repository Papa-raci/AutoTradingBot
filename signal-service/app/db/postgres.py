import asyncpg
from app.core.config import signal_settings

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Создает пул соединений при старте."""
        if not self.pool:
            print("Создание пула подключений к PostgreSQL...")
            self.pool = await asyncpg.create_pool(
                user=signal_settings.POSTGRES_USER,
                password=signal_settings.POSTGRES_PASSWORD,
                database=signal_settings.POSTGRES_DB,
                host=signal_settings.POSTGRES_HOST,
                port=signal_settings.POSTGRES_PORT,
                min_size=1,
                max_size=10
            )

    async def disconnect(self):
        """Закрывает пул."""
        if self.pool:
            await self.pool.close()
            print("Пул подключений PostgreSQL закрыт.")

    async def get_connection(self):
        """Возвращает соединение из пула."""
        return self.pool.acquire()

db = Database()