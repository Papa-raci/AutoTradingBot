class OrderCheckerRepository:
    """Проверяет наличие активных сделок."""

    def __init__(self, connection):
        self.conn = connection

    async def is_position_active(self, symbol: str) -> bool:
        """Проверка, есть ли уже открытая сделка."""
        query = "SELECT 1 FROM orders WHERE symbol = $1 AND is_active = TRUE LIMIT 1"
        val = await self.conn.fetchval(query, symbol)
        return val is not None
