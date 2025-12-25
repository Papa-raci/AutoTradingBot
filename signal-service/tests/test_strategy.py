import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.strategy import SignalStrategyService

# --- ДАННЫЕ ДЛЯ ТЕСТОВ ---
# 1. Идеальный фон (Растущий тренд)
MOCK_BG_UP = {
    "start_price": 100,
    "end_price": 150,           
    "total_period_volume": 6000
}

# 2. Плохой фон (Падающий тренд)
MOCK_BG_DOWN = {
    "start_price": 150,
    "end_price": 100,           
    "total_period_volume": 6000
}

# 3. Идеальная сигнальная свеча (Красная + Всплеск объема)
MOCK_SIG_PERFECT = {
    "open": 140,
    "close": 135,               
    "volume": 300              
}

# 4. Свеча без объема
MOCK_SIG_LOW_VOL = {
    "open": 140,
    "close": 135,
    "volume": 150
}

@pytest.fixture
def strategy_service(mocker):
    """Фикстура создает сервис с замоканными зависимостями."""
    mock_db = mocker.patch("app.services.strategy.db")
    mock_db.pool.acquire = MagicMock()
    
    mock_conn = AsyncMock()
    mock_db.pool.acquire.return_value.__aenter__.return_value = mock_conn

    mocker.patch("app.services.strategy.OrderCheckerRepository.is_position_active", return_value=False)
    
    service = SignalStrategyService()
    service.candle_repo = MagicMock()
    service.rabbitmq_channel = AsyncMock()
    
    return service

@pytest.mark.asyncio
async def test_signal_generated_perfect_conditions(strategy_service):
    """Сценарий: Всё идеально -> Сигнал отправлен."""
    strategy_service.candle_repo.get_daily_stats.return_value = MOCK_SIG_PERFECT
    strategy_service.candle_repo.get_background_stats.return_value = MOCK_BG_UP

    await strategy_service._process_symbol("BTCUSDT")

    assert strategy_service.rabbitmq_channel.publish_signal.called
    args = strategy_service.rabbitmq_channel.publish_signal.call_args[0][0]
    assert args["action"] == "OPEN_LONG"
    assert args["symbol"] == "BTCUSDT"

@pytest.mark.asyncio
async def test_no_signal_trend_down(strategy_service):
    """Сценарий: Тренд падает -> Тишина."""
    strategy_service.candle_repo.get_daily_stats.return_value = MOCK_SIG_PERFECT
    strategy_service.candle_repo.get_background_stats.return_value = MOCK_BG_DOWN

    await strategy_service._process_symbol("BTCUSDT")

    assert not strategy_service.rabbitmq_channel.publish_signal.called

@pytest.mark.asyncio
async def test_no_signal_low_volume(strategy_service):
    """Сценарий: Объема мало -> Тишина."""
    strategy_service.candle_repo.get_daily_stats.return_value = MOCK_SIG_LOW_VOL
    strategy_service.candle_repo.get_background_stats.return_value = MOCK_BG_UP

    await strategy_service._process_symbol("BTCUSDT")

    assert not strategy_service.rabbitmq_channel.publish_signal.called

@pytest.mark.asyncio
async def test_no_signal_if_position_exists(strategy_service, mocker):
    """Сценарий: Позиция уже открыта -> Тишина."""
    mocker.patch("app.services.strategy.OrderCheckerRepository.is_position_active", return_value=True)
    
    strategy_service.candle_repo.get_daily_stats.return_value = MOCK_SIG_PERFECT
    strategy_service.candle_repo.get_background_stats.return_value = MOCK_BG_UP

    await strategy_service._process_symbol("BTCUSDT")

    assert not strategy_service.rabbitmq_channel.publish_signal.called