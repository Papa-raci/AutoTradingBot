import json
from pydantic_settings import BaseSettings


class BinanceSettings(BaseSettings):
    # Настройки подключения к Analytics DB (ClickHouse)
    CLICKHOUSE_HOST: str
    CLICKHOUSE_PORT: int
    CLICKHOUSE_DB: str
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str

    # Настройки BINANCE
    # WebSocket URL для Spot API
    BINANCE_WS_URL: str
    # REST URL (на случай фоллбека)
    BINANCE_REST_URL: str

    TARGET_SYMBOLS_JSON: str

    @property
    def TARGET_SYMBOLS(self) -> list:
        try:
            return json.loads(self.TARGET_SYMBOLS_JSON)
        except json.JSONDecodeError:
            return ["BTCUSDT"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = BinanceSettings()
