from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Order
from datetime import datetime


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(self, order: Order):
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_active_orders(self):
        """Возвращает все открытые сделки."""
        result = await self.db.execute(select(Order).filter(Order.is_active))
        return result.scalars().all()

    async def get_active_order_by_symbol(self, symbol: str):
        """Проверка, есть ли уже открытая сделка по этому символу."""
        result = await self.db.execute(
            select(Order).filter(Order.symbol == symbol, Order.is_active)
        )
        return result.scalars().first()

    async def close_order(self, order_id: int, reason: str, pnl: float = 0.0):
        """Помечает ордер как закрытый."""
        order = await self.db.get(Order, order_id)
        if order:
            order.is_active = False             # type: ignore
            order.closed_at = datetime.now()
            order.exit_reason = reason
            order.pnl = pnl
            await self.db.commit()

    async def update_sl_tp(self, order_id: int, new_sl: float, new_tp: float):
        """Обновляет уровни стопов (трейлинг)."""
        order = await self.db.get(Order, order_id)
        if order:
            order.stop_loss = new_sl            # type: ignore
            order.take_profit = new_tp          # type: ignore
            await self.db.commit()
