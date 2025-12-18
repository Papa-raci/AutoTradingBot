import clickhouse_connect
from app.core.config import signal_settings


class ClickHouseClient:
    """Клиент для подключения к ClickHouse (только чтение для Signal Service)."""

    def __init__(self):
        self.client = None

    def connect(self):
        """Устанавливает подключение к ClickHouse."""
        try:
            self.client = clickhouse_connect.get_client(
                host=signal_settings.CLICKHOUSE_HOST,
                port=signal_settings.CLICKHOUSE_PORT,
                username=signal_settings.CLICKHOUSE_USER,
                password=signal_settings.CLICKHOUSE_PASSWORD,
                database=signal_settings.CLICKHOUSE_DB,
            )
            print("Подключение к ClickHouse (Signal Service) установлено.")

        except Exception as e:
            print(f"Ошибка подключения к сClickHouse: {e}")
            raise e

    def get_client(self):
        """Возвращает клиент ClickHouse."""
        return self.client


ch_client = ClickHouseClient()
