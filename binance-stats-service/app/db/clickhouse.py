import clickhouse_connect
from app.core.config import settings


class ClickHouseService:
    def __init__(self):
        self.client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB,
        )

    def init_schema(self):
        """Создает таблицу для стаканов (Orderbook)."""
        print("--- Инициализация таблицы Orderbooks (Binance) ---")

        # Храним стакан как массивы цен и объемов (топ-20 уровней)
        self.client.command(
            f"""
        CREATE TABLE IF NOT EXISTS {settings.CLICKHOUSE_DB}.orderbooks (
            timestamp DateTime64(3),
            symbol LowCardinality(String),
            bids_price Array(Float64),
            bids_qty Array(Float64),
            asks_price Array(Float64),
            asks_qty Array(Float64)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timestamp)
        TTL timestamp + INTERVAL 1 MONTH
        """
        )
        print("Таблица Orderbooks готова.")


ch_service = ClickHouseService()
