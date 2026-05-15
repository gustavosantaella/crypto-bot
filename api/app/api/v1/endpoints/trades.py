from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Trade
from app.schemas.schemas import Trade as TradeSchema, TradeBase, TradeListResponse
from app.services.exchange_service import exchange_service
from pydantic import BaseModel

router = APIRouter()

class ForceTradeRequest(BaseModel):
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    sl: float
    tp: float

@router.get("/", response_model=TradeListResponse)
def get_trades(
    skip: int = 0, 
    limit: int = 10, 
    status: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_db)
):
    query = db.query(Trade)
    
    if status == 'cancelled':
        query = query.filter(Trade.message != None, Trade.message != "")
    
        
    if start_date and start_date.strip():
        query = query.filter(Trade.timestamp >= start_date)
    if end_date and end_date.strip():
        query = query.filter(Trade.timestamp <= end_date)
        
    total = query.count()
    trades = query.order_by(Trade.timestamp.desc()).offset(skip).limit(limit).all()
    return {"total": total, "trades": trades}

@router.post("/", response_model=TradeSchema)
def create_trade(trade: TradeBase, db: Session = Depends(get_db)):
    db_trade = Trade(**trade.model_dump())
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

@router.post("/force")
def force_trade(req: ForceTradeRequest, db: Session = Depends(get_db)):
    # 1. Execute market order
    order = exchange_service.execute_market_order(req.symbol, req.side, req.quantity)
    if not order:
        raise HTTPException(status_code=400, detail="Failed to execute market order")
    
    # 2. Set SL and TP
    orders = exchange_service.set_sl_tp(req.symbol, req.side, req.sl, req.tp, req.quantity)
    
    # 3. Save to DB
    price = exchange_service.get_ticker_price(req.symbol) or 0.0
    
    db_trade = Trade(
        symbol=req.symbol,
        side='LONG' if req.side == 'BUY' else 'SHORT',
        price=price,
        quantity=req.quantity,
        pnl=0.0,
        status='open'
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    return {"status": "success", "order": order, "sl_tp": orders, "trade": db_trade}
