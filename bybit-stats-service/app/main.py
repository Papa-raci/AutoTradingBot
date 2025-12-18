import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.clickhouse import ch_service
from app.services.collector import ByBitCollector

# Глобальная переменная для хранения задачи
collector_task = None
collector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.
    """
    global collector_task, collector

    print("--- Старт: Сервис сбора статистики ByBit ---")

    # 1. Инициализация Базы Данных
    try:
        ch_service.init_schema()
        print("Схема ClickHouse успешно инициализирована.")
    except Exception as e:
        print(f"Критическая ошибка: Не удалось инициализировать БД: {e}")

    # 2. Запуск Коллектора в фоне
    collector = ByBitCollector()
    collector_task = asyncio.create_task(collector.start())
    print("Фоновая задача коллектора запущена.")

    yield

    # 3. Завершение работы
    print("Остановка сервиса...")
    if collector:
        collector.running = False

    if collector_task:
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            print("Задача коллектора остановлена.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check():
    if collector and collector.running:
        return {"status": "healthy", "service": "ByBit Stats"}
    return {"status": "starting_or_error", "service": "ByBit Stats"}
