import asyncio
import json
import websockets
import aiohttp
from datetime import datetime, timedelta
from app.core.config import stats_settings
from app.repositories.tick_repo import TickRepository
from app.db.clickhouse import ch_service
from app.db.rabbit import rabbit_publisher


class ByBitCollector:
    """Сборщик тиков с ByBit Linear."""

    def __init__(self):
        self.ws_url = stats_settings.BYBIT_WS_URL
        self.rest_url = stats_settings.BYBIT_REST_URL
        self.symbols = stats_settings.TARGET_SYMBOLS
        self.running = False

        # Буфер для накопления тиков перед записью в БД
        self.buffer = []
        self.batch_size = 1000

        self.repo = TickRepository(ch_service.client)

        # Для отслеживания разрывов связи
        self.last_update_time = {}

    async def start(self):
        """Главный цикл запуска сервиса."""
        self.running = True

        # 1. ЗАГРУЗКА ИСТОРИИ (BACKFILL)
        await self._initial_backfill()

        # 2. Запуск фоновой задачи сброса буфера в БД
        asyncio.create_task(self._flush_timer())

        # 3. Подключение к RabbitMQ
        await rabbit_publisher.connect()

        # 4. Основной цикл WebSocket
        while self.running:
            try:
                await self._check_and_fill_gaps()

                async with websockets.connect(self.ws_url) as ws:
                    print(f"ByBit WS подключен. Подписка на: {self.symbols}")

                    args = [f"publicTrade.{s}" for s in self.symbols]
                    await ws.send(json.dumps({"op": "subscribe", "args": args}))

                    async for message in ws:
                        data = json.loads(message)

                        if "topic" in data and "publicTrade" in data["topic"]:
                            await self._process_trade_msg(data)

                        elif "op" in data and data["op"] == "ping":
                            await ws.send(json.dumps({"op": "pong"}))

            except Exception as e:
                print(f"Разрыв WS соединения: {e}. Пауза 5 сек перед реконнектом...")
                await asyncio.sleep(5)

    async def _initial_backfill(self):
        """Проверяет наличие данных в БД и скачивает историю за 60 дней при необходимости."""
        print("Проверка целостности истории данных...")
        for symbol in self.symbols:
            try:
                # Проверяем, сколько свечей уже есть в базе
                query = f"SELECT count() FROM {stats_settings.CLICKHOUSE_DB}.candles_1m WHERE symbol='{symbol}'"
                res = ch_service.client.query(query)
                count = res.result_rows[0][0]

                if count < 1000:  # Если данных мало, считаем базу пустой
                    print(
                        f"История для {symbol} почти пуста. Скачиваем 60 (+5 с запасом) дней через REST API..."
                    )
                    await self._fetch_kline_history(symbol, days=65)
                else:
                    print(
                        f"История для {symbol} уже существует ({count} свечей). Пропуск скачивания."
                    )
            except Exception as e:
                print(f"Ошибка при проверке истории для {symbol}: {e}")

    async def _fetch_kline_history(self, symbol: str, days: int):
        """Качает минутные свечи через REST и пишет напрямую в candles_1m."""
        end_ts = int(datetime.now().timestamp() * 1000)
        start_ts = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        current_start = start_ts

        async with aiohttp.ClientSession() as session:
            while current_start < end_ts:
                params = {
                    "category": "linear",
                    "symbol": symbol,
                    "interval": "1",
                    "start": current_start,
                    "limit": 200,
                }

                try:
                    async with session.get(
                        f"{self.rest_url}/v5/market/kline", params=params
                    ) as resp:
                        data = await resp.json()

                        if data["retCode"] != 0:
                            print(f"Ошибка REST ByBit: {data}")
                            break

                        candles = data["result"]["list"]
                        if not candles:
                            break

                        rows = []
                        for c in candles:
                            ts_dt = datetime.fromtimestamp(int(c[0]) / 1000)
                            rows.append(
                                [
                                    ts_dt,
                                    symbol,
                                    float(c[1]),
                                    float(c[2]),
                                    float(c[3]),
                                    float(c[4]),
                                    float(c[5]),
                                    float(c[6]),
                                ]
                            )

                        ch_service.client.insert(
                            f"{stats_settings.CLICKHOUSE_DB}.candles_1m",
                            rows,
                            column_names=[
                                "timestamp",
                                "symbol",
                                "open",
                                "high",
                                "low",
                                "close",
                                "volume",
                                "turnover",
                            ],
                        )

                        current_start += 200 * 60 * 1000

                        last_candle_time = rows[0][0]
                        print(
                            f"... скачан блок истории для {symbol}. Прогресс: {last_candle_time}"
                        )

                        await asyncio.sleep(0.1)

                except Exception as e:
                    print(f"Ошибка при скачивании истории: {e}")
                    break

    async def _check_and_fill_gaps(self):
        """
        Если обнаружили пропуск > 1 мин, скачиваем пропущенный кусок через REST.
        """
        now = datetime.now()
        gap_threshold = 15

        for symbol in self.symbols:
            last = self.last_update_time.get(symbol)
            if last and (now - last).total_seconds() > gap_threshold:
                print(f"GAP DETECTED: Пропуск данных для {symbol} с {last} по {now}.")
                print(f"Начинаю восстановление истории (Gap Filling)...")
                
                try:
                    await self._fetch_kline_history(symbol, days=0.2)
                    print(f"Пропуск для {symbol} успешно заполнен.")
                except Exception as e:
                    print(f"Ошибка восстановления данных: {e}")

                self.last_update_time[symbol] = now
            if not last:
                 self.last_update_time[symbol] = now

    async def _process_trade_msg(self, msg: dict):
        """Обрабатывает входящее сообщение с тиками."""
        for t in msg.get("data", []):
            price = float(t["p"])
            symbol = t["s"]
            ts_iso = datetime.now().isoformat()

            # 1. Обновляем время последнего тика
            self.last_update_time[symbol] = datetime.now()

            # 2. Отправка цены в RabbitMQ
            asyncio.create_task(rabbit_publisher.publish_price(symbol, price, ts_iso))

            # 3. Подготовка строки для ClickHouse
            row = [
                datetime.fromtimestamp(int(t["T"]) / 1000),
                symbol,
                price,
                float(t["v"]),
                t["S"],
                t["L"],
                t["i"],
            ]
            self.buffer.append(row)

            # Если буфер переполнен - сбрасываем
            if len(self.buffer) >= self.batch_size:
                await self._flush_buffer()

    async def _flush_timer(self):
        """Фоновая задача: сбрасывает буфер каждую секунду."""
        while self.running:
            await asyncio.sleep(1.0)
            if self.buffer:
                await self._flush_buffer()

    async def _flush_buffer(self):
        """Записывает накопленные тики в ClickHouse."""
        if not self.buffer:
            return

        data_to_write = self.buffer[:]
        self.buffer.clear()

        try:
            await asyncio.to_thread(self.repo.insert_ticks, data_to_write)
        except Exception as e:
            print(f"Ошибка записи тиков в ClickHouse: {e}")
