import aio_pika
import json
import asyncio
from app.core.config import stats_settings


class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        """Подключается к RabbitMQ и создает Fanout Exchange."""
        while True:
            try:
                self.connection = await aio_pika.connect_robust(
                    host=stats_settings.RABBITMQ_HOST,
                    port=stats_settings.RABBITMQ_PORT,
                    login=stats_settings.RABBITMQ_USER,
                    password=stats_settings.RABBITMQ_PASSWORD,
                )
                self.channel = await self.connection.channel()

                self.exchange = await self.channel.declare_exchange(
                    "market_data_feed", aio_pika.ExchangeType.FANOUT
                )
                print("RabbitMQ Publisher подключен (Exchange: market_data_feed)")
                break
            except Exception as e:
                print(f"Ошибка подключения RabbitMQ: {e}. Реконнект через 5 сек...")
                await asyncio.sleep(5)

    async def publish_price(self, symbol: str, price: float, timestamp: str):
        """Отправляет обновление цены."""
        if not self.exchange:
            return

        message_body = {
            "type": "price_update",
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp,
        }

        message = aio_pika.Message(
            body=json.dumps(message_body).encode(),
            delivery_mode=aio_pika.DeliveryMode.NOT_PERSISTENT,
        )

        await self.exchange.publish(message, routing_key="")

    async def close(self):
        if self.connection:
            await self.connection.close()


rabbit_publisher = RabbitMQPublisher()
