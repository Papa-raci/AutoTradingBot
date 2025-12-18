from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order


class OrderCheckerRepository:
    """Проверяет наличие активных сделок в Orders DB."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_position_active(self, symbol: str) -> bool:
        """Проверка, есть ли уже открытая сделка по этому символу."""
        result = await self.db.execute(
            select(Order.id).filter(Order.symbol == symbol, Order.is_active)
        )
        return result.scalar_one_or_none() is not None
