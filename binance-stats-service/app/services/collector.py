import asyncio
import json
import websockets
from datetime import datetime
from app.core.config import settings
from app.db.clickhouse import ch_service
from app.repositories.orderbook_repo import OrderbookRepository


class BinanceCollector:
    """Сборщик стакана (Depth) с Binance."""

    def __init__(self):
        self.ws_base = settings.BINANCE_WS_URL
        self.symbols = [s.lower() for s in settings.TARGET_SYMBOLS]
        self.running = False
        self.buffer = []
        self.batch_size = 100
        self.repo = OrderbookRepository(ch_service.client)

    async def start(self):
        self.running = True

        # Формируем URL стрима
        streams = "/".join([f"{s}@depth20@100ms" for s in self.symbols])
        url = f"{self.ws_base}/{streams}"

        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    print(f"Binance WS подключен к {url}")

                    async for message in ws:
                        data = json.loads(message)
                        await self._process_depth_msg(data)

            except Exception as e:
                print(f"Binance WS ошибка: {e}. Реконнект через 5 сек...")
                await asyncio.sleep(5)

    async def _process_depth_msg(self, data: dict):
        if "bids" not in data or "asks" not in data:
            return

        ts = datetime.now()

        bids_p = [float(x[0]) for x in data["bids"]]
        bids_q = [float(x[1]) for x in data["bids"]]
        asks_p = [float(x[0]) for x in data["asks"]]
        asks_q = [float(x[1]) for x in data["asks"]]

        symbol = settings.TARGET_SYMBOLS[0]

        row = [ts, symbol, bids_p, bids_q, asks_p, asks_q]
        self.buffer.append(row)

        if len(self.buffer) >= self.batch_size:
            await self._flush()

    async def _flush(self):
        if not self.buffer:
            return

        data = self.buffer[:]
        self.buffer.clear()

        try:
            await asyncio.to_thread(self.repo.insert_orderbooks, data)
        except Exception as e:
            print(f"Ошибка записи Binance Orderbook: {e}")
