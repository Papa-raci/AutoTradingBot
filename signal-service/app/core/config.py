import json
from pydantic_settings import BaseSettings


class SignalSettings(BaseSettings):
    # ClickHouse Settings
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_DB: str
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str

    # RabbitMQ
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_QUEUE_SIGNALS: str

    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Strategy Settings
    TARGET_SYMBOLS_JSON: str

    @property
    def TARGET_SYMBOLS(self) -> list[str]:
        """Парсит JSON строку в список."""
        try:
            return json.loads(self.TARGET_SYMBOLS_JSON)
        except json.JSONDecodeError:
            return ["BTCUSDT"]

    @property
    def POSTGRES_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


signal_settings = SignalSettings()
