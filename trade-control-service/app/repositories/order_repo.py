from datetime import datetime

class OrderRepository:
    def __init__(self, connection):
        self.conn = connection

    async def create_order(self, order_data: dict):
        """
        Создает ордер. 
        Принимает словарь (dict) вместо объекта Order.
        """
        query = """
            INSERT INTO orders (symbol, side, entry_price, quantity, stop_loss, take_profit, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, created_at
        """
        row = await self.conn.fetchrow(
            query,
            order_data["symbol"],
            order_data["side"],
            order_data["entry_price"],
            order_data["quantity"],
            order_data["stop_loss"],
            order_data["take_profit"],
            True
        )
        return row["id"]

    async def get_active_orders(self):
        """Возвращает список активных ордеров (как словари)."""
        query = "SELECT * FROM orders WHERE is_active = TRUE"
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]

    async def get_active_order_by_symbol(self, symbol: str):
        """Ищет активный ордер по символу."""
        query = "SELECT * FROM orders WHERE symbol = $1 AND is_active = TRUE LIMIT 1"
        row = await self.conn.fetchrow(query, symbol)
        return dict(row) if row else None

    async def close_order(self, order_id: int, reason: str, pnl: float = 0.0):
        """Закрывает ордер."""
        query = """
            UPDATE orders 
            SET is_active = FALSE, closed_at = $1, exit_reason = $2, pnl = $3 
            WHERE id = $4
        """
        await self.conn.execute(query, datetime.now(), reason, pnl, order_id)

    async def update_sl_tp(self, order_id: int, new_sl: float, new_tp: float):
        """Обновляет стопы."""
        query = """
            UPDATE orders 
            SET stop_loss = $1, take_profit = $2, updated_at = NOW()
            WHERE id = $3
        """
        await self.conn.execute(query, new_sl, new_tp, order_id)