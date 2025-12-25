from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.clickhouse import ch_client
from app.db.rabbitmq import rabbit_client
from app.db.postgres import db
from app.db.models import CREATE_ORDERS_TABLE_SQL
from app.services.strategy import SignalStrategyService
from app.core.config import signal_settings


scheduler = AsyncIOScheduler()
strategy_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global strategy_service

    # 1. Инициализация подключений
    ch_client.connect()
    await rabbit_client.connect()
    await db.connect()

    async with db.pool.acquire() as conn:
        await conn.execute(CREATE_ORDERS_TABLE_SQL)
    print("Схема базы данных проверена.")

    # 2. Инициализация сервиса
    strategy_service = SignalStrategyService()

    # 3. Планировщик: Запуск каждый день в 00:00 UTC
    scheduler.add_job(
        strategy_service.analyze_and_signal,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        args=[signal_settings.TARGET_SYMBOLS],
        id="daily_signal_analysis",
        replace_existing=True,
    )

    scheduler.start()
    print("Сигнальный сервис запущен. Задание запланировано на 00:00 по UTC")

    try:
        await strategy_service.analyze_and_signal(signal_settings.TARGET_SYMBOLS)
    except Exception as e:
        print(f"Ошибка при первичном анализе: {e}")

    yield

    scheduler.shutdown()
    await rabbit_client.close()
    await db.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    """Эндпоинт для проверки работоспособности (Healthcheck)."""
    return {"status": "ok", "service": "Signal Service"}


@app.post("/force-analyze")
async def force_analyze(background_tasks: BackgroundTasks):
    """Эндпоинт для принудительного запуска анализа."""
    if strategy_service:
        background_tasks.add_task(
            strategy_service.analyze_and_signal, signal_settings.TARGET_SYMBOLS
        )
        return {"status": "processing", "message": "Анализ запущен в фоновом режиме."}
    return {"status": "error", "message": "Сервис стратегии не инициализирован."}
