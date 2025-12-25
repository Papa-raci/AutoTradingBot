import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.rabbit_consumer import start_consumer
from app.services.trader import TradingService
from app.services.notifier import RabbitNotifier
from app.db.postgres import db
from app.db.models import CREATE_ORDERS_TABLE_SQL


notifier = RabbitNotifier()

# Фоновая задача: бесконечный цикл мониторинга
async def monitoring_loop():
    print("Запуск цикла мониторинга позиций (каждые 5 сек)...")
    while True:
        try:
            async with db.pool.acquire() as conn:
                trader = TradingService(conn)
                await trader.monitor_positions()
        except Exception as e:
            print(f"Критическая ошибка в цикле мониторинга: {e}")

        await asyncio.sleep(5)


@asynccontextmanager  
async def lifespan(app: FastAPI):
    # 1. Создаем таблицы в PostgreSQL
    await db.connect()
    async with db.pool.acquire() as conn:
        await conn.execute(CREATE_ORDERS_TABLE_SQL)
    print("Схема базы данных инициализирована.")

    # 2. Запускаем RabbitMQ Consumer
    consumer_task = asyncio.create_task(start_consumer())

    # 3. Запускаем Monitoring Loop
    monitor_task = asyncio.create_task(monitoring_loop())

    yield

    # Корректное завершение при остановке контейнера
    print("Остановка сервисов...")
    await db.disconnect()
    consumer_task.cancel()
    await notifier.send_notification(
        "🤖 SYSTEM OFFLINE 🔴\nТорговый модуль остановлен."
    )
    monitor_task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Trade Control Service"}
