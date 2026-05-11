from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Trade
from app.schemas.schemas import Trade as TradeSchema, TradeBase, TradeListResponse

router = APIRouter()

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
    elif status == 'executed':
        query = query.filter((Trade.message == None) | (Trade.message == ""))
        
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
