import pytest
from unittest.mock import AsyncMock
from app.repositories.order_repo import OrderRepository

@pytest.fixture
def mock_conn():
    """
    Создает Mock соединения asyncpg.
    """
    conn = AsyncMock()

    conn.fetchrow.return_value = {"id": 1, "created_at": "2025-12-25"}
    
    conn.fetch.return_value = [
        {
            "id": 1, 
            "symbol": "ETHUSDT", 
            "side": "Buy", 
            "entry_price": 2000.0, 
            "quantity": 0.5, 
            "stop_loss": 1900.0, 
            "take_profit": 2500.0, 
            "is_active": True
        }
    ]
    return conn

@pytest.mark.asyncio
async def test_create_order(mock_conn):
    """Тест: create_order должен отправить правильный INSERT запрос."""
    repo = OrderRepository(mock_conn)

    order_data = {
        "symbol": "ETHUSDT",
        "side": "Buy",
        "entry_price": 2000.0,
        "quantity": 0.5,
        "stop_loss": 1900.0,
        "take_profit": 2500.0
    }
    
    order_id = await repo.create_order(order_data)

    assert order_id == 1
    assert mock_conn.fetchrow.called

    args = mock_conn.fetchrow.call_args[0]
    sql_query = args[0]
    
    assert "INSERT INTO orders" in sql_query
    assert args[1] == "ETHUSDT"
    assert args[3] == 2000.0

@pytest.mark.asyncio
async def test_get_active_orders(mock_conn):
    """Тест: получение списка активных ордеров."""
    repo = OrderRepository(mock_conn)

    orders = await repo.get_active_orders()

    assert len(orders) == 1
    assert orders[0]["symbol"] == "ETHUSDT"

    assert mock_conn.fetch.called
    sql_query = mock_conn.fetch.call_args[0][0]
    assert "SELECT * FROM orders WHERE is_active = TRUE" in sql_query

@pytest.mark.asyncio
async def test_close_order(mock_conn):
    """Тест: закрытие ордера."""
    repo = OrderRepository(mock_conn)

    await repo.close_order(order_id=1, reason="Test_Exit", pnl=5.0)

    assert mock_conn.execute.called
    
    args = mock_conn.execute.call_args[0]
    sql_query = args[0]
    
    assert "UPDATE orders" in sql_query
    assert "is_active = FALSE" in sql_query
    assert args[2] == "Test_Exit"
    assert args[3] == 5.0
    assert args[4] == 1

@pytest.mark.asyncio
async def test_update_sl_tp(mock_conn):
    """Тест: обновление стопов."""
    repo = OrderRepository(mock_conn)

    await repo.update_sl_tp(order_id=1, new_sl=105.0, new_tp=160.0)

    assert mock_conn.execute.called
    
    args = mock_conn.execute.call_args[0]
    sql_query = args[0]
    
    assert "UPDATE orders" in sql_query
    assert "stop_loss = $1" in sql_query
    assert args[1] == 105.0
    assert args[2] == 160.0
    assert args[3] == 1