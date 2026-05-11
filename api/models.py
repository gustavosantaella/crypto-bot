from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean
from database import Base
import datetime

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20))
    side = Column(String(10))
    price = Column(Numeric(20, 8))
    quantity = Column(Numeric(20, 8))
    balance_before = Column(Numeric(20, 8))
    pnl = Column(Numeric(20, 8))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class PriceLog(Base):
    __tablename__ = "price_logs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20))
    price = Column(Numeric(20, 8))
    rsi = Column(Numeric(10, 4))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class BotStatus(Base):
    __tablename__ = "bot_status"

    id = Column(Integer, primary_key=True, index=True)
    has_position = Column(Boolean)
    last_buy_price = Column(Numeric(20, 8))
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
