import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.postgres import engine, Base
from app.db.postgres import AsyncSessionLocal
from app.services.rabbit_consumer import start_consumer
from app.services.trader import TradingService


# Фоновая задача: бесконечный цикл мониторинга
async def monitoring_loop():
    print("Запуск цикла мониторинга позиций (каждые 5 сек)...")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                trader = TradingService(db)
                await trader.monitor_positions()
        except Exception as e:
            print(f"Критическая ошибка в цикле мониторинга: {e}")

        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Создаем таблицы в PostgreSQL
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Схема базы данных инициализирована.")

    # 2. Запускаем RabbitMQ Consumer
    consumer_task = asyncio.create_task(start_consumer())

    # 3. Запускаем Monitoring Loop
    monitor_task = asyncio.create_task(monitoring_loop())

    yield

    # Корректное завершение при остановке контейнера
    print("Остановка сервисов...")
    consumer_task.cancel()
    monitor_task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Trade Control Service"}
