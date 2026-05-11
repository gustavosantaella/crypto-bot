from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database
from database import engine, get_db
from exchange import ExchangeManager

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crypto Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Crypto Bot API is running"}

@app.get("/trades")
def get_trades(
    skip: int = 0, 
    limit: int = 10, 
    status: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Trade)
    
    if status == 'cancelled':
        query = query.filter(models.Trade.message != None)
    elif status == 'executed':
        query = query.filter(models.Trade.message == None)
        
    if start_date:
        query = query.filter(models.Trade.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Trade.timestamp <= end_date)
        
    total = query.count()
    trades = query.order_by(models.Trade.timestamp.desc()).offset(skip).limit(limit).all()
    return {"total": total, "trades": trades}

@app.get("/price-logs")
def get_price_logs(
    skip: int = 0, 
    limit: int = 15, 
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_db)
):
    query = db.query(models.PriceLog)
    
    if start_date:
        query = query.filter(models.PriceLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.PriceLog.timestamp <= end_date)
        
    total = query.count()
    logs = query.order_by(models.PriceLog.timestamp.desc()).offset(skip).limit(limit).all()
    return {"total": total, "logs": logs}

@app.get("/bot-status", response_model=schemas.BotStatus)
def get_bot_status(db: Session = Depends(get_db)):
    status = db.query(models.BotStatus).order_by(models.BotStatus.updated_at.desc()).first()
    if not status:
        return {"has_position": False, "last_buy_price": 0, "id": 0, "updated_at": "2026-01-01T00:00:00"}
    return status

@app.post("/bot-status", response_model=schemas.BotStatus)
def update_bot_status(status: schemas.BotStatusBase, db: Session = Depends(get_db)):
    db_status = models.BotStatus(**status.dict())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@app.post("/trades", response_model=schemas.Trade)
def create_trade(trade: schemas.TradeBase, db: Session = Depends(get_db)):
    db_trade = models.Trade(**trade.dict())
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

@app.post("/price-logs", response_model=schemas.PriceLog)
def create_price_log(log: schemas.PriceLogBase, db: Session = Depends(get_db)):
    db_log = models.PriceLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


# current balance
exchange_manager = ExchangeManager()

@app.get("/balance", response_model=schemas.BalanceResponse)
def get_balance():
    balances = exchange_manager.get_all_balances()
    return {"balances": balances}