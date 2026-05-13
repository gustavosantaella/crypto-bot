from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# ── Trade ──────────────────────────────────────────────────────────────────────
class TradeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    symbol:         str
    side:           str
    price:          Decimal
    quantity:       Decimal
    balance_before: Decimal
    pnl:            Optional[Decimal] = 0
    target_tp:      Optional[Decimal] = None
    target_sl:      Optional[Decimal] = None
    trade_type:     Optional[str] = "LONG"
    dca_level:      Optional[int] = 1
    message:        Optional[str] = None

class Trade(TradeBase):
    id:        int
    timestamp: datetime

class TradeListResponse(BaseModel):
    total:  int
    trades: List[Trade]

# ── Price Log ──────────────────────────────────────────────────────────────────
class PriceLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    symbol:       str
    price:        Decimal
    rsi:          Decimal
    adx:          Optional[Decimal] = None
    ema_fast:     Optional[Decimal] = None
    ema_slow:     Optional[Decimal] = None
    volume_ratio: Optional[Decimal] = None
    atr:          Optional[Decimal] = None

class PriceLog(PriceLogBase):
    id:        int
    timestamp: datetime

class PriceLogListResponse(BaseModel):
    total: int
    logs:  List[PriceLog]

# ── Bot Status ─────────────────────────────────────────────────────────────────
class BotStatusBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    has_position:       bool
    last_buy_price:     Optional[Decimal]
    target_take_profit: Optional[Decimal]
    target_stop_loss:   Optional[Decimal]
    trade_type:         str

class BotStatus(BotStatusBase):
    id:         int
    updated_at: datetime

# ── Balance ────────────────────────────────────────────────────────────────────
class AssetBalance(BaseModel):
    asset:  str
    free:   str
    locked: str

class BalanceResponse(BaseModel):
    balances: List[AssetBalance]

# ── Statistics ─────────────────────────────────────────────────────────────────
class StatsSummary(BaseModel):
    total_trades:    int
    total_buys:      int
    total_sells:     int
    winning_trades:  int
    losing_trades:   int
    win_rate:        float
    total_pnl:       float
    avg_pnl:         float
    best_trade:      float
    worst_trade:     float
    total_volume:    float
    current_streak:  int    # + positivo = racha ganadora, - negativo = perdedora
    avg_hold_time_h: float  # horas promedio entre BUY y SELL

class DailyPnL(BaseModel):
    date:     str
    pnl:      float
    trades:   int

class DailyPnLResponse(BaseModel):
    series: List[DailyPnL]

class RSIDistribution(BaseModel):
    range:  str    # e.g. "25-30"
    count:  int

class RSIDistributionResponse(BaseModel):
    buckets: List[RSIDistribution]

class HealthStatus(BaseModel):
    api_online:      bool
    last_price_log:  Optional[datetime]
    bot_alive:       bool        # True si hay precio_log en los últimos 30s
    last_signal:     str
    uptime_seconds:  float
