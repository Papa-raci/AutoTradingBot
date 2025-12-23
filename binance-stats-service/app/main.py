import asyncio
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.db.clickhouse import ch_service
from app.services.collector import BinanceCollector

collector_task = None
collector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Старт: Binance Stats Service ---")
    try:
        ch_service.init_schema()
        print("Схема ClickHouse (Orderbooks) готова.")
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")

    collector = BinanceCollector()
    app.state.collector = collector 
    
    global collector_task
    collector_task = asyncio.create_task(collector.start())
    print("Коллектор Binance запущен и сохранен в state.")

    yield

    print("Остановка сервиса...")
    if hasattr(app.state, "collector"):
        app.state.collector.running = False
    
    if collector_task:
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health_check(request: Request):
    if not hasattr(request.app.state, "collector"):
        return {"status": "starting", "details": "Collector not initialized yet"}

    collector = request.app.state.collector
    
    if collector.running:
        return {"status": "healthy", "service": "Binance Stats"}
    
    return {"status": "stopped", "service": "Binance Stats"}
