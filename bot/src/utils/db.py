from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Boolean
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

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

def log_trade(symbol, side, price, quantity, balance_before=None, pnl=None):
    db = SessionLocal()
    try:
        trade = Trade(symbol=symbol, side=side, price=price, quantity=quantity, balance_before=balance_before, pnl=pnl)
        db.add(trade)
        db.commit()
    finally:
        db.close()

def log_price(symbol, price, rsi):
    db = SessionLocal()
    try:
        log = PriceLog(symbol=symbol, price=price, rsi=rsi)
        db.add(log)
        db.commit()
    finally:
        db.close()

def update_status(has_position, last_buy_price):
    db = SessionLocal()
    try:
        status = BotStatus(has_position=has_position, last_buy_price=last_buy_price)
        db.add(status)
        db.commit()
    finally:
        db.close()
