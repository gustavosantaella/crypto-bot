"""
telegram_notifier.py — Notificaciones Telegram del Bot

Envía alertas formateadas a Telegram en dos modalidades:
  1. Eventos inmediatos: apertura/cierre de trades, breakeven, errores.
  2. Resumen periódico: estado del mercado cada STATUS_INTERVAL segundos.
"""

import time
import requests
import logging
from src.config.settings import TELEGRAM_TOKEN, TELEGRAM_ID

# Intervalo entre resúmenes de estado (5 minutos)
STATUS_INTERVAL = 300
_last_status_sent: float = 0.0


class TelegramNotifier:

    # ─────────────────────────────────────────────────────────────────────────
    # Core: envío de mensajes
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def send_message(text: str):
        if not TELEGRAM_TOKEN or not TELEGRAM_ID:
            logging.warning("Telegram credentials not set. Notification skipped.")
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code != 200:
                logging.error(f"Telegram error: {response.text}")
        except Exception as e:
            logging.error(f"Telegram exception: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Eventos inmediatos
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def notify_trade_open(symbol, side, price, qty, tp, sl):
        tp_str = f"${tp:.4f}" if tp else "N/A"
        sl_str = f"${sl:.4f}" if sl else "N/A"
        msg = (
            f"🚀 *OPERACIÓN ABIERTA*\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"🔹 *Par:* `{symbol}`\n"
            f"🔹 *Tipo:* `{side}` _(Futures)_\n"
            f"🔹 *Precio entrada:* `${price:.4f}`\n"
            f"🔹 *Cantidad:* `{qty:.4f} SOL`\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"🎯 *Take Profit:* `{tp_str}`\n"
            f"🛑 *Stop Loss:* `{sl_str}`"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_breakeven(symbol, price, new_sl, tp):
        msg = (
            f"🛡️ *BREAKEVEN ACTIVADO*\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"🔹 *Par:* `{symbol}`\n"
            f"🔹 *Precio actual:* `${price:.4f}`\n"
            f"✅ *Nuevo SL:* `${new_sl:.4f}` _(breakeven)_\n"
            f"🎯 *TP objetivo:* `${tp:.4f}`\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"_Peor resultado posible: empate 😐_"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_trade_close(symbol, side, price, qty, pnl):
        icon = "💰" if pnl > 0 else "📉"
        status = "GANANCIA ✅" if pnl > 0 else "PÉRDIDA ❌"
        msg = (
            f"{icon} *OPERACIÓN CERRADA*\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"🔹 *Par:* `{symbol}`\n"
            f"🔹 *Tipo:* `{side}` _(Cierre)_\n"
            f"🔹 *Precio salida:* `${price:.4f}`\n"
            f"🔹 *Cantidad:* `{qty}`\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"💵 *PnL Realizado:* `{pnl:+.4f} USDT` — {status}"
        )
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_error(context: str, error: str):
        """Alerta inmediata cuando ocurre un error en la ejecución."""
        msg = (
            f"🔴 *ERROR DEL BOT*\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"📍 *Contexto:* `{context}`\n"
            f"⚠️ *Detalle:* `{str(error)[:300]}`"
        )
        TelegramNotifier.send_message(msg)

    # ─────────────────────────────────────────────────────────────────────────
    # Resumen periódico de estado (cada STATUS_INTERVAL segundos)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def maybe_send_status(symbol, price, ind, dyn, has_position,
                          avg_price, target_tp, target_sl,
                          dca_count, max_dca, breakeven):
        """
        Envía un resumen de estado solo si han pasado STATUS_INTERVAL segundos
        desde el último envío. Diseñado para ser llamado en cada ciclo sin
        generar spam.
        """
        global _last_status_sent
        now = time.time()
        if now - _last_status_sent < STATUS_INTERVAL:
            return
        _last_status_sent = now

        rsi     = ind.get('rsi', 0)
        adx     = ind.get('adx', 0)
        ema200  = ind.get('ema_slow', 0)
        vol     = ind.get('volume_ratio', 0)
        mode    = dyn.get('mode_active', 'N/A')
        umbral  = dyn.get('rsi_oversold', 0)

        # Señal de tendencia
        trend_icon = "📈" if price > ema200 else "📉"
        pos_icon   = "🟢" if has_position else "⚫"

        msg = (
            f"📊 *ESTADO DEL BOT — {symbol}*\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"{trend_icon} *Precio:* `${price:.4f}`\n"
            f"📡 *RSI:* `{rsi:.1f}` _(umbral activo: {umbral:.0f})_\n"
            f"📏 *ADX:* `{adx:.1f}` | *EMA200:* `${ema200:.2f}`\n"
            f"🔊 *Volumen:* `{vol:.2f}x` del promedio\n"
            f"🧠 *Modo adaptador:* `{mode}`\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"{pos_icon} *Posición:* {'ABIERTA' if has_position else 'Sin posición'}\n"
        )

        if not has_position:
            msg += f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            msg += f"🔍 *Condiciones para Entrar:*\n"
            
            conditions_met = True
            
            # Check RSI
            if rsi >= umbral:
                msg += f"❌ *RSI:* `{rsi:.1f}` (Debe ser < {umbral:.0f})\n"
                conditions_met = False
            else:
                msg += f"✅ *RSI:* `{rsi:.1f}` (< {umbral:.0f})\n"
                
            # Check EMA200
            if ema200 > 0:
                req_price = ema200 * 1.003
                if price <= req_price:
                    msg += f"❌ *Precio:* `${price:.2f}` (Debe ser > `${req_price:.2f}` [EMA200+0.3%])\n"
                    conditions_met = False
                else:
                    msg += f"✅ *Precio:* `${price:.2f}` (> `${req_price:.2f}`)\n"
            
            # Check ADX
            if adx > 25:
                msg += f"⚠️ *ADX:* `{adx:.1f}` (Tendencia fuerte, riesgo)\n"
            else:
                msg += f"✅ *ADX:* `{adx:.1f}` (< 25)\n"

            if conditions_met:
                msg += f"⏳ *Todo listo. Esperando giro de RSI o cierre de vela.*\n"

        if has_position and avg_price:
            pnl_pct = ((price - avg_price) / avg_price) * 100
            pnl_icon = "🟢" if pnl_pct >= 0 else "🔴"
            msg += (
                f"💹 *Avg entrada:* `${avg_price:.4f}`\n"
                f"{pnl_icon} *PnL no realizado:* `{pnl_pct:+.2f}%`\n"
                f"🎯 *TP:* `${target_tp:.4f}` | 🛑 *SL:* `${target_sl:.4f}`\n"
                f"📦 *DCA:* `{dca_count}/{max_dca}` entradas\n"
                f"🛡️ *Breakeven:* `{'ON' if breakeven else 'OFF'}`\n"
            )

        TelegramNotifier.send_message(msg)
