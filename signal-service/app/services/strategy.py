import asyncio
from datetime import datetime, timedelta, timezone

from app.repositories.candle_repo import CandleRepository
from app.db.rabbitmq import rabbit_client
from app.db.clickhouse import ch_client
from app.db.postgres import AsyncSessionLocal
from app.repositories.order_checker_repo import OrderCheckerRepository


class SignalStrategyService:

    def __init__(self):
        # Получаем клиент из глобального объекта (он уже подключен в main.py)
        self.candle_repo = CandleRepository(ch_client.get_client())
        self.rabbitmq_channel = rabbit_client

    async def _process_symbol(self, symbol: str):
        """Логика анализа для одного символа."""
        now = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # 1. Определяем периоды
        # Сигнальный день: Вчера (полные сутки)
        signal_day_end = now
        signal_day_start = now - timedelta(days=1)

        # Фоновый период: 60 дней ДО сигнального дня
        background_end = signal_day_start
        background_start = background_end - timedelta(days=60)

        print(
            f"Анализ {symbol}: SignalDay={signal_day_start.date()}, Background={background_start.date()}-{background_end.date()}"
        )

        # 2. Проверка активных позиций (чтобы не дублировать сделки)
        async with AsyncSessionLocal() as db:
            order_checker = OrderCheckerRepository(db)
            if await order_checker.is_position_active(symbol):
                print(f"Активная позиция по {symbol} уже существует. Пропуск.")
                return

        # 3. Получение данных из ClickHouse
        sig_data = self.candle_repo.get_daily_stats(
            symbol, signal_day_start, signal_day_end
        )
        bg_data = self.candle_repo.get_background_stats(
            symbol, background_start, background_end
        )

        if not sig_data or not bg_data:
            print(
                f"Недостаточно данных для {symbol} (нужно ждать накопления истории)."
            )
            return

        # 4. Проверка условий стратегии (ИСПРАВЛЕННАЯ ЛОГИКА)

        # Условие А: Растущий ТРЕНД фона (Close конца > Close начала)
        trend_is_up = bg_data["end_price"] > bg_data["start_price"]

        # Условие Б: КРАСНАЯ СВЕЧА сигнального дня (Close < Open)
        candle_is_red = sig_data["close"] < sig_data["open"]

        # Условие В: ВСПЛЕСК ОБЪЕМА
        # Средний дневной объем за фон = Общий объем / 60
        avg_daily_volume = bg_data["total_period_volume"] / 60

        # Объем сигнального дня должен быть БОЛЬШЕ (>) чем 2 * средний
        volume_spike = sig_data["volume"] > (2 * avg_daily_volume)

        print(
            f"SYM: {symbol} | TrendUp: {trend_is_up} | RedCandle: {candle_is_red} | VolSpike: {volume_spike} "
            f"(Vol: {sig_data['volume']:.2f} vs 2xAvg: {2*avg_daily_volume:.2f})"
        )

        # 5. Генерация сигнала
        if trend_is_up and candle_is_red and volume_spike:
            print(f"ГЕНЕРАЦИЯ СИГНАЛА LONG для {symbol}!")

            signal_payload = {
                "action": "OPEN_LONG",
                "symbol": symbol,
                "entry_price": sig_data["close"],  # Для информации
                "signal_time": datetime.now(timezone.utc).isoformat(),
            }
            await self.rabbitmq_channel.publish_signal(signal_payload)

    async def analyze_and_signal(self, symbols: list[str]):
        """
        Основной метод. Запускается по расписанию.
        """
        print(f"--- Запуск анализа сигналов: {datetime.now(timezone.utc)} ---")
        if not self.rabbitmq_channel.channel:
            print("RabbitMQ канал не готов, попытка переподключения...")
            await self.rabbitmq_channel.connect()

        tasks = [self._process_symbol(symbol) for symbol in symbols]
        await asyncio.gather(*tasks)
        print("--- Анализ завершен ---")
