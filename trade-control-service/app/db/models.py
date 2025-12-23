from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from app.db.postgres import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # "Buy" / "Sell"

    entry_price = Column(Float)
    quantity = Column(Float)

    stop_loss = Column(Float)
    take_profit = Column(Float)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    closed_at = Column(DateTime(timezone=True), nullable=True)
    exit_reason = Column(String, nullable=True)  # "TP", "SL", "Manual", "Signal"
    pnl = Column(Float, nullable=True)           # Прибыль в USDT