import logging
from aiogram import Bot
from app.core.config import notification_settings

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.bot = Bot(token=notification_settings.TELEGRAM_BOT_TOKEN)

    async def send_message(self, text: str):
        """Отправляет сообщение в заданный чат."""
        try:
            await self.bot.send_message(chat_id=notification_settings.TELEGRAM_CHAT_ID, text=text)
            logger.info(f"TG Sent: {text[:30]}...")
        except Exception as e:
            logger.error(f"TG Error: {e}")
            
    async def close(self):
        await self.bot.session.close()