import decimal
from datetime import datetime, timezone
from app.repositories.order_repo import OrderRepository
from app.infrastructure.bybit_client import client as bybit
from app.core.config import control_settings
from app.services.notifier import RabbitNotifier


def quantize_value(value: float, step: float) -> float:
    """Округляет value до шага step (вниз)."""
    step_dec = decimal.Decimal(str(step))
    value_dec = decimal.Decimal(str(value))
    quantized_value = value_dec.quantize(step_dec, rounding=decimal.ROUND_DOWN)
    return float(quantized_value)


class TradingService:

    _last_report_date = None

    def __init__(self, db_session):
        self.repo = OrderRepository(db_session)
        self.notifier = RabbitNotifier()

    async def process_signal(self, signal: dict):
        """
        Главный метод обработки сигналов.
        Маршрутизирует действия OPEN/CLOSE.
        """
        action = signal.get("action")
        symbol = signal.get("symbol")
        qty_override = signal.get("quantity")

        if not action or not symbol:
            print(f"Некорректный сигнал: {signal}")
            return

        print(f"ОБРАБОТКА СИГНАЛА: {action} {symbol}")

        if action == "OPEN_LONG":
            await self.open_long_position(symbol, qty_override=qty_override)
        
        elif action == "CLOSE_LONG":
            await self.close_long_position(symbol)
            
        else:
            print(f"Неизвестная команда: {action}")

    async def open_long_position(self, symbol: str, qty_override: float = None):
        """
        Открывает позицию.
        Сразу ставит SL (-5%) и TP (+25%).
        """
        existing = await self.repo.get_active_order_by_symbol(symbol)
        if existing:
            print(f"Сделка по {symbol} уже существует. Пропуск.")
            return

        print(f"--- ОТКРЫТИЕ LONG: {symbol} ---")
        try:
            bybit.set_leverage(symbol, control_settings.LEVERAGE)
            info = bybit.get_instrument_info(symbol)
            current_price = bybit.get_current_price(symbol)

            qty_step = info["qtyStep"]
            min_qty = info["minOrderQty"]
            tick_size = info["tickSize"]

            if qty_override:
                quantity = quantize_value(qty_override, qty_step)
            else:
                raw_qty = control_settings.TRADE_AMOUNT_USDT / current_price
                quantity = quantize_value(raw_qty, qty_step)

            if quantity < min_qty:
                print(f"Объем {quantity} меньше минимального {min_qty}. Отмена.")
                return

            sl_price = quantize_value(current_price * 0.95, tick_size)
            tp_price = quantize_value(current_price * 1.25, tick_size)

            # 1. Ордер
            result = bybit.place_market_order(symbol, "Buy", quantity)
            if not result:
                print("Биржа не приняла ордер.")
                return

            # 2. Стопы
            bybit.set_trading_stop(symbol, sl=sl_price, tp=tp_price)

            print(
                f"LONG открыт: {symbol} по цене {current_price}. SL={sl_price}, TP={tp_price}"
            )

            # 3. Уведомление в TG
            msg = (
                f"🚀 OPEN LONG: {symbol}\n"
                f"Entry: {current_price}\n"
                f"TP: {tp_price}\n"
                f"SL: {sl_price}\n"
                f"Size: {quantity}"
            )
            await self.notifier.send_notification(msg)

            # 4. Сохранение в БД
            new_order_data = {
                "symbol": symbol,
                "side": "Buy",
                "entry_price": current_price,
                "quantity": quantity,
                "stop_loss": sl_price,
                "take_profit": tp_price
            }
            await self.repo.create_order(new_order_data)

        except Exception as e:
            print(f"Ошибка открытия {symbol}: {e}")
            err_msg = (
                f"⚠️ CRITICAL ERROR: {symbol}\n"
                f"Не удалось открыть ордер!\n"
                f"Error: {e}"
            )
            await self.notifier.send_notification(err_msg)

    async def close_long_position(self, symbol: str):
        """
        Закрывает позицию (продажа + обновление БД).
        """
        print(f"--- ЗАКРЫТИЕ LONG: {symbol} ---")
        
        # 1. Ищем активный ордер в нашей БД
        order = await self.repo.get_active_order_by_symbol(symbol)
        if not order:
            print(f"В БД нет активной сделки по {symbol}. Пытаюсь закрыть на бирже принудительно...")
        
        try:
            # 2. Закрываем на бирже
            bybit.close_position(symbol)
            print(f"Позиция {symbol} закрыта на бирже.")

            # 3. Закрываем в БД
            if order:
                await self.repo.close_order(order["id"], reason="Сигнал_CLOSE_LONG")
                print(f"Статус в БД обновлен (id={order["id"]}).")

            msg = f"💰 CLOSED LONG: {symbol}\nСделка закрыта."
            await self.notifier.send_notification(msg)
                
        except Exception as e:
            print(f"Ошибка закрытия {symbol}: {e}")
            err_msg = (
                f"⚠️ CRITICAL ERROR: {symbol}\n"
                f"Не удалось закрыть позицию!\n"
                f"Error: {e}"
            )
            await self.notifier.send_notification(err_msg)

    async def monitor_positions(self):
        """
        Фоновый мониторинг
        """
        active_orders = await self.repo.get_active_orders()
        now = datetime.now(timezone.utc)
        today = now.date()

        target_hour = 2         # UTC
        
        if now.hour == target_hour and TradingService._last_report_date != today:
            try:
                print("Формирование ежедневного отчета...")
                balance = bybit.get_wallet_balance("USDT")
                active_count = len(active_orders)
                
                msg = (
                    f"☕ MORNING REPORT\n"
                    f"📅 {today}\n"
                    f"💰 Balance: ${balance:.2f}\n"
                    f"📊 Active Positions: {active_count}\n"
                    f"System Status: OK 🟢"
                )
                await self.notifier.send_notification(msg)
                
                TradingService._last_report_date = today
                
            except Exception as e:
                print(f"Ошибка отправки отчета: {e}")

        is_daily_update_time = (
            now.hour == 0 and now.minute == 0 and 0 <= now.second < 10
        )

        for order in active_orders:
            # --- РАСПАКОВКА ДАННЫХ ---
            symbol = order["symbol"]
            order_id = order["id"]
            entry_price = order["entry_price"]
            current_sl = order["stop_loss"]
            current_tp = order["take_profit"]
            created_at = order["created_at"]

            try:
                # --- СИНХРОНИЗАЦИЯ С БИРЖЕЙ ---
                pos_info = bybit.get_position_info(symbol)

                # A. Если позиции нет на бирже
                if pos_info["size"] == 0:
                    print(
                        f"Позиция {symbol} не найдена на бирже (закрыта). Обновляем БД."
                    )
                    await self.repo.close_order(
                        order_id, reason="Ручной_или_SLTP_Выход"
                    )

                    msg = (
                        f"🔔 POSITION CLOSED: {symbol}\n"
                        f"Сработал StopLoss или TakeProfit на бирже.\n"
                        f"Сделка завершена."
                    )
                    await self.notifier.send_notification(msg)

                    continue

                # B. Ручные изменения
                exchange_sl = pos_info["stopLoss"]
                exchange_tp = pos_info["takeProfit"]

                sl_changed = abs(exchange_sl - current_sl) > 1e-9
                tp_changed = abs(exchange_tp - current_tp) > 1e-9

                if sl_changed or tp_changed:
                    print(f"Синхронизация {symbol}: Стопы изменены. БД обновлена.")
                    await self.repo.update_sl_tp(order_id, exchange_sl, exchange_tp)

                    current_sl = exchange_sl
                    current_tp = exchange_tp

                    msg = (
                        f"🔄 SYNC UPDATE: {symbol}\n"
                        f"TP\SL изменены вручную.\n"
                        f"TP: {current_tp}\n"
                        f"SL: {exchange_sl}"
                    )
                    await self.notifier.send_notification(msg)

                # --- ПРОВЕРКА 24 ЧАСА ---
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
                age = now - created_at
                current_price = bybit.get_current_price(symbol)

                if age.total_seconds() > 86400:  # 24 часа
                    pnl_pct = (current_price - entry_price) / entry_price
                    if pnl_pct < 0:
                        print(f"Выход по таймеру {symbol}. PnL: {pnl_pct:.2%}")
                        bybit.close_position(symbol)
                        await self.repo.close_order(order_id, reason="Убыток_по_таймеру")
                        continue

                # --- ЕЖЕДНЕВНОЕ ОБНОВЛЕНИЕ (Трейлинг раз в сутки) ---
                if is_daily_update_time:
                    is_profitable = current_price > entry_price

                    if is_profitable:
                        info = bybit.get_instrument_info(symbol)
                        tick_size = info["tickSize"]

                        new_sl = quantize_value(current_price * 0.95, tick_size)
                        new_tp = quantize_value(current_price * 1.25, tick_size)

                        if new_sl > current_sl:
                            print(f"Daily Update {symbol}: Поднимаем SL -> {new_sl}")
                            bybit.set_trading_stop(symbol, sl=new_sl, tp=new_tp)
                            await self.repo.update_sl_tp(order_id, new_sl, new_tp)

                            msg = (
                                f"📈 TRAILING STOP: {symbol}\n"
                                f"Стоп подтянут вверх!\n"
                                f"Price: {current_price}\n"
                                f"New SL: {new_sl}"
                            )
                            await self.notifier.send_notification(msg)

            except Exception as e:
                print(f"Ошибка мониторинга {symbol}: {e}")
