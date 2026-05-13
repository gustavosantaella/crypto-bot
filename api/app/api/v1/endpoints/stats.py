from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.models import Trade, PriceLog
from app.schemas.schemas import StatsSummary, DailyPnLResponse, DailyPnL, RSIDistributionResponse, RSIDistribution, HealthStatus
from datetime import datetime, timedelta
from typing import Optional
import time

router = APIRouter()

_start_time = time.time()

@router.get("/summary", response_model=StatsSummary)
def get_stats_summary(db: Session = Depends(get_db)):
    """Estadísticas globales de rendimiento del bot."""
    all_sells = db.query(Trade).filter(Trade.side == "SELL").all()
    all_buys  = db.query(Trade).filter(Trade.side == "BUY").all()

    winning = [t for t in all_sells if t.pnl and float(t.pnl) > 0]
    losing  = [t for t in all_sells if t.pnl and float(t.pnl) < 0]

    total_pnl  = sum(float(t.pnl) for t in all_sells if t.pnl)
    pnl_values = [float(t.pnl) for t in all_sells if t.pnl]

    total_volume = sum(float(t.price) * float(t.quantity) for t in all_buys)

    # Racha actual (desde el último trade hasta ahora)
    streak = 0
    for trade in reversed(all_sells):
        if trade.pnl:
            val = float(trade.pnl)
            if streak == 0:
                streak = 1 if val > 0 else -1
            elif streak > 0 and val > 0:
                streak += 1
            elif streak < 0 and val < 0:
                streak -= 1
            else:
                break

    # Tiempo promedio de hold (BUY → SELL)
    buy_times  = sorted([t.timestamp for t in all_buys], reverse=True)
    sell_times = sorted([t.timestamp for t in all_sells], reverse=True)
    hold_times = []
    for sell_t in sell_times:
        buys_before = [b for b in buy_times if b < sell_t]
        if buys_before:
            hold_times.append((sell_t - max(buys_before)).total_seconds() / 3600)

    avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0

    return StatsSummary(
        total_trades   = len(all_buys) + len(all_sells),
        total_buys     = len(all_buys),
        total_sells    = len(all_sells),
        winning_trades = len(winning),
        losing_trades  = len(losing),
        win_rate       = (len(winning) / len(all_sells) * 100) if all_sells else 0,
        total_pnl      = total_pnl,
        avg_pnl        = (total_pnl / len(all_sells)) if all_sells else 0,
        best_trade     = max(pnl_values) if pnl_values else 0,
        worst_trade    = min(pnl_values) if pnl_values else 0,
        total_volume   = total_volume,
        current_streak = streak,
        avg_hold_time_h= round(avg_hold, 2),
    )


@router.get("/pnl-over-time", response_model=DailyPnLResponse)
def get_pnl_over_time(days: int = 30, db: Session = Depends(get_db)):
    """PnL acumulado por día para el gráfico de rendimiento."""
    since = datetime.utcnow() - timedelta(days=days)
    sells = db.query(Trade).filter(
        Trade.side == "SELL",
        Trade.timestamp >= since
    ).order_by(Trade.timestamp).all()

    daily: dict = {}
    for trade in sells:
        day_key = trade.timestamp.strftime("%Y-%m-%d")
        if day_key not in daily:
            daily[day_key] = {"pnl": 0.0, "trades": 0}
        daily[day_key]["pnl"]    += float(trade.pnl) if trade.pnl else 0
        daily[day_key]["trades"] += 1

    series = [
        DailyPnL(date=k, pnl=round(v["pnl"], 4), trades=v["trades"])
        for k, v in sorted(daily.items())
    ]
    return DailyPnLResponse(series=series)


@router.get("/rsi-distribution", response_model=RSIDistributionResponse)
def get_rsi_distribution(db: Session = Depends(get_db)):
    """Distribución de RSI en las entradas BUY (calidad de señales)."""
    buys = db.query(Trade).filter(Trade.side == "BUY").all()

    # Buscar el RSI del price_log más cercano a cada trade BUY
    buckets = {
        "0-20": 0, "20-25": 0, "25-30": 0, "30-35": 0,
        "35-40": 0, "40-50": 0, "50-60": 0, "60-70": 0, "70+": 0
    }

    for trade in buys:
        # Buscar el price_log más cercano en tiempo
        log = db.query(PriceLog).filter(
            PriceLog.timestamp <= trade.timestamp
        ).order_by(PriceLog.timestamp.desc()).first()

        if log and log.rsi:
            rsi = float(log.rsi)
            if   rsi <  20: buckets["0-20"]   += 1
            elif rsi <  25: buckets["20-25"]  += 1
            elif rsi <  30: buckets["25-30"]  += 1
            elif rsi <  35: buckets["30-35"]  += 1
            elif rsi <  40: buckets["35-40"]  += 1
            elif rsi <  50: buckets["40-50"]  += 1
            elif rsi <  60: buckets["50-60"]  += 1
            elif rsi <  70: buckets["60-70"]  += 1
            else:            buckets["70+"]    += 1

    return RSIDistributionResponse(
        buckets=[RSIDistribution(range=k, count=v) for k, v in buckets.items()]
    )


@router.get("/health", response_model=HealthStatus)
def get_health(db: Session = Depends(get_db)):
    """Estado de salud del bot — detecta si está vivo basándose en el último price_log."""
    last_log = db.query(PriceLog).order_by(PriceLog.timestamp.desc()).first()

    now = datetime.utcnow()
    bot_alive = False
    last_signal = "UNKNOWN"

    if last_log:
        age_seconds = (now - last_log.timestamp).total_seconds()
        bot_alive = age_seconds < 60  # Vivo si hay log en el último minuto

    return HealthStatus(
        api_online     = True,
        last_price_log = last_log.timestamp if last_log else None,
        bot_alive      = bot_alive,
        last_signal    = last_signal,
        uptime_seconds = round(time.time() - _start_time, 1),
    )
