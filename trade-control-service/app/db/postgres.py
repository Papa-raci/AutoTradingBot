import asyncpg
from app.core.config import control_settings

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Создает пул соединений при старте."""
        if not self.pool:
            print("Создание пула подключений к PostgreSQL...")
            self.pool = await asyncpg.create_pool(
                user=control_settings.POSTGRES_USER,
                password=control_settings.POSTGRES_PASSWORD,
                database=control_settings.POSTGRES_DB,
                host=control_settings.POSTGRES_HOST,
                port=control_settings.POSTGRES_PORT,
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
