import requests
import logging
from src.config.settings import TELEGRAM_TOKEN, TELEGRAM_ID

class TelegramNotifier:
    @staticmethod
    def send_message(text):
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
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                logging.error(f"Error sending Telegram notification: {response.text}")
        except Exception as e:
            logging.error(f"Exception sending Telegram notification: {e}")

    @staticmethod
    def notify_trade_open(symbol, side, price, qty, tp, sl):
        msg = f"🚀 *OPERACIÓN ABIERTA*\n\n"
        msg += f"🔸 *Símbolo:* {symbol}\n"
        msg += f"🔸 *Tipo:* {side} (Futures)\n"
        msg += f"🔸 *Precio:* ${price:.4f}\n"
        if qty and qty > 0:
            msg += f"🔸 *Cantidad:* {qty:.4f}\n"
        tp_str = f"${tp:.4f}" if tp else "N/A"
        sl_str = f"${sl:.4f}" if sl else "N/A"
        msg += f"🎯 *Take Profit:* {tp_str}\n"
        msg += f"🛑 *Stop Loss:* {sl_str}"
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_breakeven(symbol, price, new_sl, tp):
        """Notifica cuando el Stop Loss se mueve al precio de entrada (breakeven)."""
        msg = f"🛡️ *BREAKEVEN ACTIVADO*\n\n"
        msg += f"🔸 *Símbolo:* {symbol}\n"
        msg += f"🔸 *Precio actual:* ${price:.4f}\n"
        msg += f"✅ *Nuevo SL (breakeven):* ${new_sl:.4f}\n"
        msg += f"🎯 *TP objetivo:* ${tp:.4f}\n"
        msg += f"\n_El peor resultado ahora es: empate 😐_"
        TelegramNotifier.send_message(msg)

    @staticmethod
    def notify_trade_close(symbol, side, price, qty, pnl):
        icon = "💰" if pnl > 0 else "📉"
        status = "GANANCIA" if pnl > 0 else "PÉRDIDA"
        
        msg = f"{icon} *OPERACIÓN CERRADA ({status})*\n\n"
        msg += f"🔹 *Símbolo:* {symbol}\n"
        msg += f"🔹 *Tipo:* {side} (Cierre)\n"
        msg += f"🔹 *Precio:* ${price:.4f}\n"
        msg += f"🔹 *Cantidad:* {qty}\n"
        msg += f"💵 *PnL:* {pnl:.4f} USDT"
        TelegramNotifier.send_message(msg)
