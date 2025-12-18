from datetime import datetime
from app.core.config import signal_settings


class CandleRepository:
    """Репозиторий для чтения свечей из ClickHouse."""

    def __init__(self, client):
        self.client = client
        self.db = signal_settings.CLICKHOUSE_DB

    def get_daily_stats(
            self, symbol: str,
            start_time: datetime,
            end_time: datetime
            ):
        """
        Получает статистику за СИГНАЛЬНЫЙ день.
        Агрегируем данные из candles_1m за указанный период.
        """

        s_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        e_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        query = f"""
        SELECT
            argMin(open, timestamp) as day_open,
            argMax(close, timestamp) as day_close,
            sum(volume) as day_volume
        FROM {self.db}.candles_1m
        WHERE symbol = '{symbol}'
          AND timestamp >= '{s_str}'
          AND timestamp < '{e_str}'
        """

        try:
            result = self.client.query(query).result_rows
            if result and result[0][0] is not None:
                return {
                    "open": result[0][0],
                    "close": result[0][1],
                    "volume": result[0][2],
                }
        except Exception as e:
            print(f"Ошибка чтения daily stats для {symbol}: {e}")
        return None

    def get_background_stats(
        self, symbol: str, start_time: datetime, end_time: datetime
    ):
        """
        Получает статистику за ФОНОВЫЙ период (60 дней).
        """
        s_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        e_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        query = f"""
        SELECT
            argMin(close, timestamp) as start_price,
            argMax(close, timestamp) as end_price,
            sum(volume) as total_volume
        FROM {self.db}.candles_1m
        WHERE symbol = '{symbol}'
          AND timestamp >= '{s_str}'
          AND timestamp < '{e_str}'
        """

        try:
            result = self.client.query(query).result_rows
            if result and result[0][0] is not None:
                return {
                    "start_price": result[0][0],
                    "end_price": result[0][1],
                    "total_period_volume": result[0][2],
                }
        except Exception as e:
            print(f"Ошибка чтения background stats для {symbol}: {e}")
        return None
