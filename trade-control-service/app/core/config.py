from pydantic_settings import BaseSettings


class ControlSettings(BaseSettings):
    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # RabbitMQ
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_QUEUE_SIGNALS: str

    # ByBit API
    BYBIT_API_KEY: str
    BYBIT_SECRET_KEY: str
    BYBIT_TESTNET: bool = False  # False для реальной торговли

    # Trading Logic
    LEVERAGE: int
    TRADE_AMOUNT_USDT: FloatingPointError
    RECV_WINDOW: int

    @property
    def POSTGRES_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


control_settings = ControlSettings()
