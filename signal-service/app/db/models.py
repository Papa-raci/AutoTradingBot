from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # "Buy" (Long)

    entry_price = Column(Float)  # Цена входа
    quantity = Column(Float)  # Размер позиции

    stop_loss = Column(Float)  # Текущий уровень SL
    take_profit = Column(Float)  # Текущий уровень TP

    is_active = Column(Boolean, default=True)  # Открыта ли сделка

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    closed_at = Column(DateTime, nullable=True)

    exit_reason = Column(String, nullable=True)  # "TP", "SL", "Time", "Signal"
    pnl = Column(Float, nullable=True)  # Прибыль/убыток
