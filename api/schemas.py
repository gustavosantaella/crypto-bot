from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class TradeBase(BaseModel):
    symbol: str
    side: str
    price: Decimal
    quantity: Decimal
    balance_before: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    target_tp: Optional[Decimal] = None
    target_sl: Optional[Decimal] = None
    trade_type: str = "LONG"

class Trade(TradeBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class PriceLogBase(BaseModel):
    symbol: str
    price: Decimal
    rsi: Optional[Decimal] = None

class PriceLog(PriceLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class BotStatusBase(BaseModel):
    has_position: bool
    last_buy_price: Optional[Decimal] = None
    target_take_profit: Optional[Decimal] = None
    target_stop_loss: Optional[Decimal] = None
    trade_type: str = "LONG"

class BotStatus(BotStatusBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class AssetBalance(BaseModel):
    asset: str
    free: str
    locked: str

class BalanceResponse(BaseModel):
    balances: List[AssetBalance]
