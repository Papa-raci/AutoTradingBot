import asyncio
import json
import aio_pika
from app.core.config import signal_settings


class RabbitMQClient:
    """Клиент для подключения к RabbitMQ и инициализации очередей."""

    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        """Устанавливает подключение к RabbitMQ и инициализирует очереди."""
        # Пытаемся подключиться 10 раз с паузой
        for attempt in range(10):
            try:
                self.connection = await aio_pika.connect_robust(
                    host=signal_settings.RABBITMQ_HOST,
                    port=signal_settings.RABBITMQ_PORT,
                    login=signal_settings.RABBITMQ_USER,
                    password=signal_settings.RABBITMQ_PASSWORD,
                )
                break
            except Exception as e:
                print(f"RabbitMQ не готов: {e}. Повтор через 3 сек ({attempt+1}/10)...")
                await asyncio.sleep(3)

        self.channel = await self.connection.channel()
        await self.channel.declare_queue(
            signal_settings.RABBITMQ_QUEUE_SIGNALS,
            durable=True,
        )
        print("Подключение к RabbitMQ установлено (Signal Service).")

    async def publish_signal(self, signal_data: dict):
        """Публикует сигнал в очередь RabbitMQ."""
        if not self.channel:
            print("Ошибка: Канал RabbitMQ не инициализирован, сигнал не отправлен.")
            return

        message = aio_pika.Message(
            body=json.dumps(signal_data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await self.channel.default_exchange.publish(
            message,
            routing_key=signal_settings.RABBITMQ_QUEUE_SIGNALS,
        )
        print(
            f"Сигнал отправлен в очередь: {signal_data.get('action')} {signal_data.get('symbol')}"
        )

    async def close(self):
        """Закрывает подключение к RabbitMQ."""
        if self.connection:
            await self.connection.close()
            print("Подключение к RabbitMQ закрыто.")


rabbit_client = RabbitMQClient()
