import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class StatsSettings(BaseSettings):
    # --- ClickHouse (Analytics DB) ---
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_DB: str
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str

    # --- RabbitMQ (Message Broker) ---
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str

    # --- ByBit Settings ---
    BYBIT_WS_URL: str
    BYBIT_REST_URL: str

    # Список монет для отслеживания.
    TARGET_SYMBOLS_JSON: str

    @property
    def TARGET_SYMBOLS(self) -> list:
        try:
            return json.loads(self.TARGET_SYMBOLS_JSON)
        except json.JSONDecodeError:
            return ["BTCUSDT"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding = "utf-8", extra="ignore")


stats_settings = StatsSettings()
