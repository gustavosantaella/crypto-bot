from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean
from app.db.session import Base
import datetime

class Trade(Base):
    __tablename__ = "trades"

    id              = Column(Integer, primary_key=True, index=True)
    symbol          = Column(String(20))
    side            = Column(String(10))
    price           = Column(Numeric(20, 8))
    quantity        = Column(Numeric(20, 8))
    balance_before  = Column(Numeric(20, 8))
    pnl             = Column(Numeric(20, 8))
    target_tp       = Column(Numeric(20, 8))
    target_sl       = Column(Numeric(20, 8))
    trade_type      = Column(String(10), default="LONG")
    dca_level       = Column(Integer, default=1)          # Nivel DCA (1=primera, 2=segunda…)
    message         = Column(String(200), nullable=True)
    timestamp       = Column(DateTime, default=datetime.datetime.utcnow)

class PriceLog(Base):
    __tablename__ = "price_logs"

    id           = Column(Integer, primary_key=True, index=True)
    symbol       = Column(String(20))
    price        = Column(Numeric(20, 8))
    rsi          = Column(Numeric(10, 4))
    adx          = Column(Numeric(10, 4), nullable=True)
    ema_fast     = Column(Numeric(20, 8), nullable=True)
    ema_slow     = Column(Numeric(20, 8), nullable=True)
    volume_ratio = Column(Numeric(10, 4), nullable=True)
    atr          = Column(Numeric(20, 8), nullable=True)
    timestamp    = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class BotStatus(Base):
    __tablename__ = "bot_status"

    id                 = Column(Integer, primary_key=True, index=True)
    has_position       = Column(Boolean)
    last_buy_price     = Column(Numeric(20, 8))
    target_take_profit = Column(Numeric(20, 8))
    target_stop_loss   = Column(Numeric(20, 8))
    trade_type         = Column(String(10), default="LONG")
    updated_at         = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
