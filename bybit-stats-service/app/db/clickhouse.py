import clickhouse_connect
from app.core.config import stats_settings


class ClickHouseService:
    def __init__(self):
        # Подключение. В docker-compose host обычно называется 'analytics_db'
        self.client = clickhouse_connect.get_client(
            host=stats_settings.CLICKHOUSE_HOST,
            port=stats_settings.CLICKHOUSE_PORT,
            username=stats_settings.CLICKHOUSE_USER,
            password=stats_settings.CLICKHOUSE_PASSWORD,
            database=stats_settings.CLICKHOUSE_DB,
        )

    def init_schema(self):
        """Создает таблицы и материализованные представления (MV)."""
        print("--- Инициализация схемы ClickHouse ---")

        # 0. Создаем базу если нет
        self.client.command(
            f"CREATE DATABASE IF NOT EXISTS {stats_settings.CLICKHOUSE_DB}"
        )

        # 1. Таблица сырых тиков
        self.client.command(
            f"""
        CREATE TABLE IF NOT EXISTS {stats_settings.CLICKHOUSE_DB}.ticks (
            timestamp DateTime64(3),
            symbol LowCardinality(String),
            price Float64,
            size Float64,
            side LowCardinality(String),
            tick_direction LowCardinality(String),
            trade_id String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timestamp)
        TTL timestamp + INTERVAL 1 MONTH
        """
        )

        # 2. Таблица минутных свечей
        self.client.command(
            f"""
        CREATE TABLE IF NOT EXISTS {stats_settings.CLICKHOUSE_DB}.candles_1m (
            timestamp DateTime,
            symbol LowCardinality(String),
            open SimpleAggregateFunction(any, Float64),
            high SimpleAggregateFunction(max, Float64),
            low SimpleAggregateFunction(min, Float64),
            close SimpleAggregateFunction(anyLast, Float64),
            volume SimpleAggregateFunction(sum, Float64),
            turnover SimpleAggregateFunction(sum, Float64)
        ) ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timestamp)
        """
        )

        # 3. MV: Тики -> Минутки
        self.client.command(
            f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {stats_settings.CLICKHOUSE_DB}.ticks_to_candles_1m_mv
        TO {stats_settings.CLICKHOUSE_DB}.candles_1m
        AS SELECT
            toStartOfMinute(t.timestamp) as timestamp,
            t.symbol as symbol,
            any(t.price) as open,
            max(t.price) as high,
            min(t.price) as low,
            anyLast(t.price) as close,
            sum(t.size) as volume,
            sum(t.price * t.size) as turnover
        FROM {stats_settings.CLICKHOUSE_DB}.ticks AS t
        GROUP BY t.symbol, toStartOfMinute(t.timestamp)
        """
        )

        # 4. Аналогично делаем для часов
        self._create_hourly_aggregation()

        print("--- Схема ClickHouse успешно инициализирована ---")

    def _create_hourly_aggregation(self):
        # Таблица часов
        self.client.command(
            f"""
        CREATE TABLE IF NOT EXISTS {stats_settings.CLICKHOUSE_DB}.candles_1h (
            timestamp DateTime,
            symbol LowCardinality(String),
            open SimpleAggregateFunction(any, Float64),
            high SimpleAggregateFunction(max, Float64),
            low SimpleAggregateFunction(min, Float64),
            close SimpleAggregateFunction(anyLast, Float64),
            volume SimpleAggregateFunction(sum, Float64),
            turnover SimpleAggregateFunction(sum, Float64)
        ) ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timestamp)
        """
        )

        # MV: Минутки -> Часы
        self.client.command(
            f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {stats_settings.CLICKHOUSE_DB}.candles_1m_to_1h_mv
        TO {stats_settings.CLICKHOUSE_DB}.candles_1h
        AS SELECT
            toStartOfHour(m.timestamp) as timestamp,
            m.symbol as symbol,
            any(m.open) as open,
            max(m.high) as high,
            min(m.low) as low,
            anyLast(m.close) as close,
            sum(m.volume) as volume,
            sum(m.turnover) as turnover
        FROM {stats_settings.CLICKHOUSE_DB}.candles_1m AS m
        GROUP BY m.symbol, toStartOfHour(m.timestamp)
        """
        )


# Глобальный инстанс
ch_service = ClickHouseService()
