import json
import logging
import asyncio
import aio_pika
from app.core.config import notification_settings
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)

async def start_consumer():
    tg_service = TelegramService()
    
    logger.info(f"Подключение к RabbitMQ: {notification_settings.RABBITMQ_HOST}")

    # Подключение с автоматическим реконнектом
    connection = None
    while True:
        try:
            connection = await aio_pika.connect_robust(
                host=notification_settings.RABBITMQ_HOST,
                port=notification_settings.RABBITMQ_PORT,
                login=notification_settings.RABBITMQ_USER,
                password=notification_settings.RABBITMQ_PASSWORD,
            )
            logger.info("RabbitMQ подключен!")
            break
        except Exception as e:
            logger.error(f"Ошибка подключения RabbitMQ: {e}. Рестарт через 5 сек...")
            await asyncio.sleep(5)

    async with connection:
        channel = await connection.channel()
        
        queue = await channel.declare_queue(
            notification_settings.RABBITMQ_QUEUE_NOTIFICATIONS, 
            durable=True
        )

        logger.info("Ожидание уведомлений...")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body)
                        text = data.get("msg", str(data))

                        await tg_service.send_message(text)
                        
                    except Exception as e:
                        logger.error(f"Ошибка обработки сообщения: {e}")
    
    await tg_service.close()