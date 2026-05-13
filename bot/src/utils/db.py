from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "crypto-bot")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine       = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class Trade(Base):
    __tablename__ = "trades"
    id             = Column(Integer, primary_key=True, index=True)
    symbol         = Column(String(20))
    side           = Column(String(10))
    price          = Column(Numeric(20, 8))
    quantity       = Column(Numeric(20, 8))
    balance_before = Column(Numeric(20, 8))
    pnl            = Column(Numeric(20, 8))
    target_tp      = Column(Numeric(20, 8))
    target_sl      = Column(Numeric(20, 8))
    trade_type     = Column(String(10), default="LONG")
    dca_level      = Column(Integer, default=1)
    message        = Column(String(200), nullable=True)
    timestamp      = Column(DateTime, default=datetime.datetime.utcnow)


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
    timestamp    = Column(DateTime, default=datetime.datetime.utcnow)


class BotStatus(Base):
    __tablename__ = "bot_status"
    id                 = Column(Integer, primary_key=True, index=True)
    has_position       = Column(Boolean)
    last_buy_price     = Column(Numeric(20, 8))
    target_take_profit = Column(Numeric(20, 8))
    target_stop_loss   = Column(Numeric(20, 8))
    trade_type         = Column(String(10), default="LONG")
    updated_at         = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


def _migrate():
    """Agrega columnas nuevas si no existen (migracion automatica simple)."""
    with engine.connect() as conn:
        # Columnas nuevas en price_logs
        new_price_cols = {
            "adx":          "DECIMAL(10,4)",
            "ema_fast":     "DECIMAL(20,8)",
            "ema_slow":     "DECIMAL(20,8)",
            "volume_ratio": "DECIMAL(10,4)",
            "atr":          "DECIMAL(20,8)",
        }
        for col, dtype in new_price_cols.items():
            try:
                conn.execute(text(f"ALTER TABLE price_logs ADD COLUMN {col} {dtype}"))
                conn.commit()
            except Exception:
                pass   # Columna ya existe

        # Columna nueva en trades
        try:
            conn.execute(text("ALTER TABLE trades ADD COLUMN dca_level INT DEFAULT 1"))
            conn.commit()
        except Exception:
            pass


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()


def log_trade(symbol, side, price, quantity, balance_before=None, pnl=None,
              target_tp=None, target_sl=None, trade_type="LONG", dca_level=1, message=None):
    db = SessionLocal()
    try:
        trade = Trade(
            symbol=symbol, side=side, price=price, quantity=quantity,
            balance_before=balance_before, pnl=pnl,
            target_tp=target_tp, target_sl=target_sl,
            trade_type=trade_type, dca_level=dca_level, message=message
        )
        db.add(trade)
        db.commit()
    finally:
        db.close()


def log_price(symbol, price, indicators: dict):
    """
    Guarda un price_log con todos los indicadores técnicos.
    indicators debe contener: rsi, adx, ema_fast, ema_slow, volume_ratio, atr
    """
    db = SessionLocal()
    try:
        log = PriceLog(
            symbol       = symbol,
            price        = price,
            rsi          = indicators.get("rsi", 0),
            adx          = indicators.get("adx"),
            ema_fast     = indicators.get("ema_fast"),
            ema_slow     = indicators.get("ema_slow"),
            volume_ratio = indicators.get("volume_ratio"),
            atr          = indicators.get("atr"),
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


def update_status(has_position, last_buy_price, target_tp=None, target_sl=None, trade_type="LONG"):
    db = SessionLocal()
    try:
        status = BotStatus(
            has_position=has_position,
            last_buy_price=last_buy_price,
            target_take_profit=target_tp,
            target_stop_loss=target_sl,
            trade_type=trade_type
        )
        db.add(status)
        db.commit()
    finally:
        db.close()


def get_last_status():
    db = SessionLocal()
    try:
        return db.query(BotStatus).order_by(BotStatus.updated_at.desc()).first()
    finally:
        db.close()
