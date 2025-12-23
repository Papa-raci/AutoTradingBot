import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.trader import TradingService

# Тестовый сигнал
SIGNAL_OPEN = {"action": "OPEN_LONG", "symbol": "SOLUSDT"}
SIGNAL_CLOSE = {"action": "CLOSE_LONG", "symbol": "SOLUSDT"}

@pytest.fixture
def trader(mocker):
    """Создает Трейдера с полным набором моков"""
    db_session = MagicMock()
    service = TradingService(db_session)

    service.repo = AsyncMock()
    service.repo.get_active_order_by_symbol.return_value = None 

    service.bybit = mocker.patch("app.services.trader.bybit")
    service.bybit.get_instrument_info.return_value = {
        "qtyStep": 0.1,         # float
        "minOrderQty": 1.0,     # float
        "tickSize": 0.01        # float
    }
    service.bybit.get_current_price.return_value = 100.0
    service.bybit.place_market_order.return_value = {"id": "123"}
 
    mocker.patch("app.services.trader.control_settings.TRADE_AMOUNT_USDT", 100.0)
    mocker.patch("app.services.trader.control_settings.LEVERAGE", 10)
    service.notifier = AsyncMock() 
    
    return service

@pytest.mark.asyncio
async def test_open_long_success(trader):
    """Сценарий: Успешное открытие лонга"""
    await trader.process_signal(SIGNAL_OPEN)

    trader.bybit.set_leverage.assert_called_with("SOLUSDT", 10)
    trader.bybit.place_market_order.assert_called_with("SOLUSDT", "Buy", 1.0) 

    call_kwargs = trader.bybit.set_trading_stop.call_args[1]
    assert call_kwargs['sl'] == 95.0
    assert call_kwargs['tp'] == 125.0

    assert trader.repo.create_order.called
    assert trader.notifier.send_notification.called

@pytest.mark.asyncio
async def test_open_long_ignored_duplicate(trader):
    """Сценарий: Сигнал пришел, но ордер в БД уже есть"""
    trader.repo.get_active_order_by_symbol.return_value = {"id": 1, "symbol": "SOLUSDT"}
    
    await trader.process_signal(SIGNAL_OPEN)

    assert not trader.bybit.place_market_order.called
    assert not trader.repo.create_order.called

@pytest.mark.asyncio
async def test_open_long_api_error(trader):
    """Сценарий: Биржа вернула ошибку при открытии"""
    trader.bybit.place_market_order.return_value = None
    
    await trader.process_signal(SIGNAL_OPEN)

    assert not trader.repo.create_order.called

@pytest.mark.asyncio
async def test_close_long_success(trader):
    """Сценарий: Закрытие позиции по сигналу"""
    mock_order = MagicMock()
    mock_order.id = 555
    trader.repo.get_active_order_by_symbol.return_value = mock_order
    
    await trader.process_signal(SIGNAL_CLOSE)
    
    trader.bybit.close_position.assert_called_with("SOLUSDT")
    trader.repo.close_order.assert_called_with(555, reason="Сигнал_CLOSE_LONG")
    assert trader.notifier.send_notification.called