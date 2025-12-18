from typing import Optional
from pybit.unified_trading import HTTP
from app.core.config import control_settings


class ByBitClient:
    def __init__(self):
        self.session = HTTP(
            testnet=control_settings.BYBIT_TESTNET,
            api_key=control_settings.BYBIT_API_KEY,
            api_secret=control_settings.BYBIT_SECRET_KEY,
            recv_window=control_settings.RECV_WINDOW,
        )

    def set_leverage(self, symbol: str, leverage: int):
        """Устанавливает кредитное плечо."""
        try:
            self.session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage),
            )
            print(f"Плечо {leverage}x установлено для {symbol}")
        except Exception as e:
            if "110043" not in str(e):
                print(f"Предупреждение при установке плеча: {e}")

    def get_current_price(self, symbol: str) -> float:
        """Получает текущую рыночную цену."""
        response = self.session.get_tickers(category="linear", symbol=symbol)
        return float(response["result"]["list"][0]["lastPrice"])

    def get_instrument_info(self, symbol: str) -> dict:
        """Получает фильтры точности (шаг лота, шаг цены)."""
        response = self.session.get_instruments_info(category="linear", symbol=symbol)
        info = response["result"]["list"][0]
        return {
            "qtyStep": float(info["lotSizeFilter"]["qtyStep"]),
            "minOrderQty": float(info["lotSizeFilter"]["minOrderQty"]),
            "tickSize": float(info["priceFilter"]["tickSize"]),
        }

    def get_position_info(self, symbol: str) -> dict:
        """
        Возвращает информацию о позиции, включая SL и TP.
        """
        response = self.session.get_positions(category="linear", symbol=symbol)
        for item in response["result"]["list"]:
            # Если size != 0, значит позиция есть
            return {
                "size": float(item["size"]),
                "avgPrice": float(item["avgPrice"]),
                "side": item["side"],
                "stopLoss": float(item["stopLoss"]) if item["stopLoss"] != "" else 0.0,
                "takeProfit": (
                    float(item["takeProfit"]) if item["takeProfit"] != "" else 0.0
                ),
            }
        return {"size": 0.0, "stopLoss": 0.0, "takeProfit": 0.0}

    def place_market_order(self, symbol: str, side: str, qty: float):
        """Размещает рыночный ордер."""
        return self.session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=str(qty),
            timeInForce="GTC",
        )

    def set_trading_stop(self, symbol: str, sl: Optional[float] = None, tp: Optional[float] = None):
        """Устанавливает SL/TP."""
        params = {"category": "linear", "symbol": symbol}
        if sl is not None:
            params["stopLoss"] = str(sl)
        if tp is not None:
            params["takeProfit"] = str(tp)

        return self.session.set_trading_stop(**params)

    def close_position(self, symbol: str):
        """Закрывает позицию по рынку."""
        pos = self.get_position_info(symbol)
        if pos["size"] > 0:
            side = "Sell" if pos["side"] == "Buy" else "Buy"
            self.place_market_order(symbol, side, pos["size"])


client = ByBitClient()
