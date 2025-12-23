import json
import aio_pika
import asyncio
from app.core.config import control_settings
from app.services.trader import TradingService
from app.db.postgres import AsyncSessionLocal
from app.services.notifier import RabbitNotifier


async def start_consumer():
    """Слушает очередь сигналов и вызывает трейдера."""
    print(f"Подключение к RabbitMQ: {control_settings.RABBITMQ_HOST}...")

    notifier = RabbitNotifier()

    connection = None
    while True:
        try:
            connection = await aio_pika.connect_robust(
                host=control_settings.RABBITMQ_HOST,
                port=control_settings.RABBITMQ_PORT,
                login=control_settings.RABBITMQ_USER,
                password=control_settings.RABBITMQ_PASSWORD,
            )
            print("RabbitMQ успешно подключен!")
            await notifier.send_notification(
                "🤖 SYSTEM ONLINE 🟢\nТорговый модуль запущен и ожидает сигналов."
            )
            break
        except Exception as e:
            print(f"Ошибка подключения к RabbitMQ: {e}. Повтор через 5 сек...")
            await asyncio.sleep(5)

    channel = await connection.channel()
    queue = await channel.declare_queue(
        control_settings.RABBITMQ_QUEUE_SIGNALS, durable=True
    )

    print("Ожидание торговых сигналов...")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    data = json.loads(message.body)
                    print(f"ПОЛУЧЕН СИГНАЛ: {data}")

                    async with AsyncSessionLocal() as db:
                        trader = TradingService(db)
                        await trader.process_signal(data)

                except Exception as e:
                    print(f"Ошибка обработки сообщения: {e}")
