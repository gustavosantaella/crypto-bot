from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import BotStatus, PriceLog
from app.schemas.schemas import BotStatus as BotStatusSchema, BotStatusBase, PriceLog as PriceLogSchema, PriceLogBase, PriceLogListResponse

router = APIRouter()

@router.get("/bot", response_model=BotStatusSchema)
def get_bot_status(db: Session = Depends(get_db)):
    status = db.query(BotStatus).order_by(BotStatus.updated_at.desc()).first()
    if not status:
        return {"has_position": False, "last_buy_price": 0, "id": 0, "updated_at": "2026-01-01T00:00:00", "target_take_profit": 0, "target_stop_loss": 0, "trade_type": "LONG"}
    return status

@router.post("/bot", response_model=BotStatusSchema)
def update_bot_status(status: BotStatusBase, db: Session = Depends(get_db)):
    db_status = BotStatus(**status.model_dump())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.get("/prices", response_model=PriceLogListResponse)
def get_price_logs(
    skip: int = 0, 
    limit: int = 15, 
    db: Session = Depends(get_db)
):
    query = db.query(PriceLog)
    total = query.count()
    logs = query.order_by(PriceLog.timestamp.desc()).offset(skip).limit(limit).all()
    return {"total": total, "logs": logs}

@router.post("/prices", response_model=PriceLogSchema)
def create_price_log(log: PriceLogBase, db: Session = Depends(get_db)):
    db_log = PriceLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
