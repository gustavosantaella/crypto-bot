import requests
import time
import threading
import logging
import os
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import BotStatus, Trade, PriceLog
from app.services.exchange_service import exchange_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramBot")

LOCK_FILE = "bot.lock"

class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self.running = False
        self._is_active_instance = False

    def send_message(self, chat_id, text, parse_mode="Markdown", show_keyboard=True):
        if not self._is_active_instance:
            return

        url = f"{self.api_url}/sendMessage"
        keyboard = {
            "keyboard": [
                [{"text": "📊 Estado"}, {"text": "💰 Balance"}],
                [{"text": "📜 Últimos Trades"}, {"text": "🆔 Mi ID"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        
        payload = {
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": parse_mode
        }
        
        if show_keyboard:
            payload["reply_markup"] = keyboard
            
        try:
            requests.post(url, json=payload)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def get_updates(self):
        url = f"{self.api_url}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 20}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("result", [])
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
        return []

    def handle_status(self, chat_id):
        db = SessionLocal()
        try:
            status = db.query(BotStatus).order_by(BotStatus.updated_at.desc()).first()
            last_price = db.query(PriceLog).order_by(PriceLog.timestamp.desc()).first()
            
            if not status:
                self.send_message(chat_id, "❌ No hay información de estado en la base de datos.")
                return

            msg = "🤖 *Estado del Bot Professional*\n\n"
            msg += f"📈 *Posición:* {'✅ ACTIVA' if status.has_position else '⏳ ESPERANDO SEÑAL'}\n"
            msg += f"🔧 *Estrategia:* {status.trade_type}\n"
            
            if status.has_position:
                msg += f"💰 *Precio Entrada:* ${float(status.last_buy_price):.2f}\n"
                msg += f"🎯 *Take Profit:* ${float(status.target_take_profit):.2f}\n"
                msg += f"🛑 *Stop Loss:* ${float(status.target_stop_loss):.2f}\n"
            
            if last_price:
                msg += f"\n📊 *Mercado Actual:*\n"
                msg += f"💵 *Precio:* ${float(last_price.price):.2f}\n"
                msg += f"⚡️ *RSI:* {float(last_price.rsi):.2f}\n"
            
            self.send_message(chat_id, msg)
        finally:
            db.close()

    def handle_trades(self, chat_id):
        db = SessionLocal()
        try:
            trades = db.query(Trade).order_by(Trade.timestamp.desc()).limit(5).all()
            if not trades:
                self.send_message(chat_id, "📭 No hay trades registrados.")
                return

            msg = "📜 *Últimos 5 Trades*\n\n"
            for t in trades:
                icon = "🟢" if (t.trade_type == "LONG" and t.side == "BUY") or (t.trade_type == "SHORT" and t.side == "SELL") else "🔴"
                msg += f"{icon} *{t.side} {t.symbol}* - ${float(t.price):.2f}\n"
                msg += f"   Qty: {t.quantity} | PnL: {float(t.pnl) if t.pnl else 0:.2f} USDT\n"
                msg += f"   📅 _{t.timestamp.strftime('%d/%m %H:%M')}_\n\n"
            
            self.send_message(chat_id, msg)
        finally:
            db.close()

    def handle_balance(self, chat_id):
        balances = exchange_service.get_all_balances()
        usdt = next((b for b in balances if b['asset'] == 'USDT'), None)
        
        if not usdt:
            self.send_message(chat_id, "❌ No se pudo obtener el balance de USDT.")
            return

        msg = "💰 *Balance en Binance Futures*\n\n"
        msg += f"💵 *Disponible:* {float(usdt['free']):.2f} USDT\n"
        msg += f"🔒 *En Posición:* {float(usdt['locked']):.2f} USDT\n"
        
        self.send_message(chat_id, msg)

    def process_message(self, message):
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text", "").lower().strip()

        # Seguridad: Solo responder al ID autorizado
        if settings.TELEGRAM_ID != 0 and user_id != settings.TELEGRAM_ID:
            logger.warning(f"Intento de acceso no autorizado de ID: {user_id}")
            self.send_message(chat_id, "🛑 *Acceso Denegado.*\nEste bot es privado y solo responde a su dueño.", show_keyboard=False)
            return

        # Mapeo robusto (ignora emojis)
        if any(kw in text for kw in ["start", "hola", "inicio"]):
            msg = "🤖 *CryptoBot Pro v2.0*\n\n"
            msg += "Bienvenido a tu centro de control personal. Usa los botones de abajo para monitorear tu operativa en tiempo real."
            self.send_message(chat_id, msg)
        elif "estado" in text or "status" in text:
            self.handle_status(chat_id)
        elif "trades" in text or "operaciones" in text:
            self.handle_trades(chat_id)
        elif "balance" in text or "saldo" in text:
            self.handle_balance(chat_id)
        elif "id" in text:
            self.send_message(chat_id, f"👤 Tu ID de Telegram es: `{user_id}`")

    def run_polling(self):
        logger.info("Telegram Bot Polling started...")
        self.running = True
        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.last_update_id = update.get("update_id", self.last_update_id)
                    if "message" in update:
                        self.process_message(update["message"])
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)

    def setup_bot_profile(self):
        try:
            commands_url = f"{self.api_url}/setMyCommands"
            commands = [
                {"command": "status", "description": "📊 Ver estado del bot"},
                {"command": "balance", "description": "💰 Consultar balance"},
                {"command": "trades", "description": "📜 Historial de trades"},
                {"command": "id", "description": "🆔 Ver mi ID"}
            ]
            requests.post(commands_url, json={"commands": commands})
        except: pass

    def start(self):
        if not self.token: return

        # Sistema de bloqueo para evitar duplicados
        if os.path.exists(LOCK_FILE):
            logger.warning("Bot already running (Lock file exists). Skipping startup.")
            return

        try:
            with open(LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))
            
            self._is_active_instance = True
            self.setup_bot_profile()
            
            thread = threading.Thread(target=self.run_polling, daemon=True)
            thread.start()
            logger.info("Telegram Bot Thread launched exclusively.")
        except Exception as e:
            logger.error(f"Failed to start bot instance: {e}")

    def stop(self):
        self.running = False
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

telegram_bot = TelegramBot()
