from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# --- Trade Schemas ---
class TradeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    side: str
    price: Decimal
    quantity: Decimal
    balance_before: Decimal
    pnl: Optional[Decimal] = 0
    target_tp: Optional[Decimal] = None
    target_sl: Optional[Decimal] = None
    trade_type: Optional[str] = "LONG"
    message: Optional[str] = None

class Trade(TradeBase):
    id: int
    timestamp: datetime

class TradeListResponse(BaseModel):
    total: int
    trades: List[Trade]

# --- Price Log Schemas ---
class PriceLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    price: Decimal
    rsi: Decimal

class PriceLog(PriceLogBase):
    id: int
    timestamp: datetime

class PriceLogListResponse(BaseModel):
    total: int
    logs: List[PriceLog]

# --- Bot Status Schemas ---
class BotStatusBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    has_position: bool
    last_buy_price: Optional[Decimal]
    target_take_profit: Optional[Decimal]
    target_stop_loss: Optional[Decimal]
    trade_type: str

class BotStatus(BotStatusBase):
    id: int
    updated_at: datetime

# --- Balance Schemas ---
class AssetBalance(BaseModel):
    asset: str
    free: str
    locked: str

class BalanceResponse(BaseModel):
    balances: List[AssetBalance]
