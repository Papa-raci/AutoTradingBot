import json
import aio_pika
from app.core.config import control_settings

class RabbitNotifier:
    def __init__(self):
        self.queue_name = "telegram_notifications" 

    async def send_notification(self, message_text: str):
        """Отправляет текст в очередь уведомлений"""
        try:
            connection = await aio_pika.connect_robust(
                host=control_settings.RABBITMQ_HOST,
                port=control_settings.RABBITMQ_PORT,
                login=control_settings.RABBITMQ_USER,
                password=control_settings.RABBITMQ_PASSWORD,
            )
            
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue(self.queue_name, durable=True)
                
                payload = {"msg": message_text}
                
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=self.queue_name,
                )
                print(f"[Notifier] Отправлено в очередь: {message_text[:20]}...")
                
        except Exception as e:
            print(f"[Notifier] Ошибка отправки: {e}")