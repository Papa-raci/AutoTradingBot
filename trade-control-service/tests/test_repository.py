import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Order
from app.repositories.order_repo import OrderRepository

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    """Создает чистую БД для каждого теста"""
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_and_get_order(db_session):
    """Тест: Создание и получение активного ордера"""
    repo = OrderRepository(db_session)

    new_order = Order(
        symbol="ETHUSDT",
        side="Buy",
        entry_price=2000.0,
        quantity=0.5,
        stop_loss=1900.0,
        take_profit=2500.0,
        is_active=True
    )
    await repo.create_order(new_order)

    saved_order = await repo.get_active_order_by_symbol("ETHUSDT")
    
    assert saved_order is not None
    assert saved_order.symbol == "ETHUSDT"
    assert saved_order.entry_price == 2000.0
    assert saved_order.is_active is True

@pytest.mark.asyncio
async def test_close_order(db_session):
    """Тест: Закрытие ордера (смена статуса)"""
    repo = OrderRepository(db_session)

    order = Order(symbol="XRPUSDT", side="Buy", entry_price=0.5, quantity=100, is_active=True)
    db_session.add(order)
    await db_session.commit()

    await repo.close_order(order.id, reason="Test_Exit")

    active = await repo.get_active_order_by_symbol("XRPUSDT")
    assert active is None

    updated_order = await db_session.get(Order, order.id)
    assert updated_order.is_active is False
    assert updated_order.exit_reason == "Test_Exit"

@pytest.mark.asyncio
async def test_update_sl_tp(db_session):
    """Тест: Обновление стопов (Трейлинг)"""
    repo = OrderRepository(db_session)
    
    order = Order(symbol="LTCUSDT", side="Buy", entry_price=100, stop_loss=90, take_profit=150, is_active=True)
    db_session.add(order)
    await db_session.commit()

    await repo.update_sl_tp(order.id, new_sl=105.0, new_tp=160.0)
    
    updated = await db_session.get(Order, order.id)
    assert updated.stop_loss == 105.0
    assert updated.take_profit == 160.0