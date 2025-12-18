from app.core.config import stats_settings


class TickRepository:
    """Репозиторий для работы с тиками в ClickHouse."""

    def __init__(self, client):
        self.client = client

    def insert_ticks(self, tick_data: list[list]):
        """Вставляет список тиков в таблицу ClickHouse."""
        if not tick_data:
            return

        try:
            self.client.insert(
                table=f"{stats_settings.CLICKHOUSE_DB}.ticks",
                data=tick_data,
                column_names=[
                    "timestamp",
                    "symbol",
                    "price",
                    "size",
                    "side",
                    "tick_direction",
                    "trade_id",
                ],
            )
        except Exception as e:
            print(f"Ошибка вставки тиков в ClickHouse: {e}")
            raise e
