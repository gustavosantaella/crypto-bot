"""
telegram_notifier.py — Professional Telegram Bot Service

Features:
  - Single-instance execution via PID-based lock files (auto-cleanup on stale locks)
  - Deduplication of messages via hash-based tracking (prevents duplicate sends)
  - Robust polling with exponential backoff on failures
  - Automatic recovery from network hangs via short polling timeouts
  - Graceful shutdown with signal handling
  - Rate limiting to respect Telegram API limits
  - All DB sessions properly scoped and closed
"""

import requests
import time
import threading
import logging
import os
import hashlib
from collections import OrderedDict
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import BotStatus, Trade, PriceLog
from app.services.exchange_service import exchange_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramBot")

LOCK_FILE = "bot.lock"

# ── Rate Limiting ─────────────────────────────────────────────────────────────
MAX_MESSAGES_PER_SECOND = 1        # Telegram allows ~30/sec but we stay safe
MIN_MESSAGE_INTERVAL = 1.0         # Seconds between sends


class MessageDeduplicator:
    """
    Tracks recently sent messages by content hash to prevent duplicates.
    Keeps a sliding window of the last N messages with timestamps.
    Messages with identical content within the TTL window are suppressed.
    """

    def __init__(self, max_entries: int = 100, ttl_seconds: float = 30.0):
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._max = max_entries
        self._ttl = ttl_seconds

    def is_duplicate(self, text: str) -> bool:
        """Returns True if this exact message was sent recently."""
        h = hashlib.md5(text.encode()).hexdigest()
        now = time.time()

        # Purge expired entries
        expired = [k for k, ts in self._cache.items() if now - ts > self._ttl]
        for k in expired:
            del self._cache[k]

        if h in self._cache:
            return True

        self._cache[h] = now

        # Evict oldest if over capacity
        while len(self._cache) > self._max:
            self._cache.popitem(last=False)

        return False


class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.last_update_id = 0
        self.running = False
        self._is_active_instance = False
        self._dedup = MessageDeduplicator(max_entries=200, ttl_seconds=60)
        self._last_send_time: float = 0.0
        self._consecutive_errors: int = 0
        self._max_backoff: float = 60.0
        self._thread: threading.Thread | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Core: Rate-limited, deduplicated message sending
    # ─────────────────────────────────────────────────────────────────────────
    def send_message(self, chat_id, text: str, parse_mode="Markdown", show_keyboard=True):
        if not self._is_active_instance or not self.token:
            return

        # Deduplication: skip identical messages within TTL window
        if self._dedup.is_duplicate(text):
            logger.debug("Duplicate message suppressed.")
            return

        # Rate limiting
        now = time.time()
        elapsed = now - self._last_send_time
        if elapsed < MIN_MESSAGE_INTERVAL:
            time.sleep(MIN_MESSAGE_INTERVAL - elapsed)

        url = f"{self.api_url}/sendMessage"
        keyboard = {
            "keyboard": [
                [{"text": "📊 Estado"}, {"text": "💰 Balance"}],
                [{"text": "📜 Últimos Trades"}, {"text": "🧠 IA Predicción"}],
                [{"text": "🆔 Mi ID"}, {"text": "❓ Ayuda"}]
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
            response = requests.post(url, json=payload, timeout=10)
            self._last_send_time = time.time()

            if response.status_code == 429:
                # Rate limited by Telegram — respect retry_after
                retry_after = response.json().get("parameters", {}).get("retry_after", 5)
                logger.warning(f"Telegram rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            elif response.status_code != 200:
                logger.error(f"Telegram send error ({response.status_code}): {response.text[:200]}")
        except requests.exceptions.Timeout:
            logger.warning("Telegram send timeout — message may not have been delivered.")
        except Exception as e:
            logger.error(f"Telegram send exception: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Polling with exponential backoff and hang protection
    # ─────────────────────────────────────────────────────────────────────────
    def get_updates(self) -> list:
        """
        Long-polls Telegram for new messages.
        Uses a 15s timeout (not 20) to prevent the thread from hanging indefinitely
        if Telegram's servers are slow or the network is unstable.
        """
        url = f"{self.api_url}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 15,          # Short enough to detect hangs
            "allowed_updates": ["message"]  # Only messages, no channel posts etc.
        }
        try:
            response = requests.get(url, params=params, timeout=20)  # HTTP timeout > long-poll timeout
            if response.status_code == 200:
                self._consecutive_errors = 0  # Reset backoff on success
                return response.json().get("result", [])
            elif response.status_code == 409:
                # Conflict: another bot instance is polling. Back off significantly.
                logger.error("Telegram 409 Conflict — another instance is polling. Stopping this instance.")
                self.running = False
                return []
            else:
                logger.error(f"Telegram getUpdates error ({response.status_code})")
                return []
        except requests.exceptions.Timeout:
            # This is the main cause of "bot getting stuck":
            # The HTTP request to Telegram hangs forever without a timeout.
            logger.warning("Telegram getUpdates timed out — retrying...")
            return []
        except requests.exceptions.ConnectionError:
            logger.warning("Telegram connection error — network may be down.")
            return []
        except Exception as e:
            logger.error(f"Telegram getUpdates exception: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Command Handlers (DB sessions are scoped per-request)
    # ─────────────────────────────────────────────────────────────────────────
    def handle_status(self, chat_id):
        db = SessionLocal()
        try:
            status = db.query(BotStatus).order_by(BotStatus.updated_at.desc()).first()
            last_price = db.query(PriceLog).order_by(PriceLog.timestamp.desc()).first()

            if not status:
                self.send_message(chat_id, "❌ No hay información de estado en la base de datos.")
                return

            pos_status = "✅ ACTIVA" if status.has_position else "⏳ ESPERANDO SEÑAL"
            msg = (
                f"🤖 *ESTADO DEL BOT*\n"
                f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                f"📈 *Posición:* {pos_status}\n"
                f"🔧 *Estrategia:* `{status.trade_type}`\n"
            )

            if status.has_position and status.last_buy_price:
                entry = float(status.last_buy_price)
                tp = float(status.target_take_profit) if status.target_take_profit else 0
                sl = float(status.target_stop_loss) if status.target_stop_loss else 0
                msg += (
                    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                    f"💰 *Precio Entrada:* `${entry:.2f}`\n"
                    f"🎯 *Take Profit:* `${tp:.2f}`\n"
                    f"🛑 *Stop Loss:* `${sl:.2f}`\n"
                )
                if last_price:
                    current = float(last_price.price)
                    pnl_pct = ((current - entry) / entry) * 100
                    pnl_icon = "🟢" if pnl_pct >= 0 else "🔴"
                    msg += f"{pnl_icon} *PnL actual:* `{pnl_pct:+.2f}%`\n"

            if last_price:
                msg += (
                    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                    f"📊 *Mercado Actual*\n"
                    f"💵 *Precio:* `${float(last_price.price):.2f}`\n"
                    f"⚡️ *RSI:* `{float(last_price.rsi):.1f}`\n"
                )

            self.send_message(chat_id, msg)
        except Exception as e:
            logger.error(f"Error in handle_status: {e}")
            self.send_message(chat_id, f"⚠️ Error al obtener estado: `{str(e)[:150]}`")
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
                pnl_val = float(t.pnl) if t.pnl else 0
                icon = "🟢" if pnl_val > 0 else ("🔴" if pnl_val < 0 else "⚪")
                msg += (
                    f"{icon} *{t.side} {t.symbol}* — `${float(t.price):.2f}`\n"
                    f"   Qty: `{t.quantity}` | PnL: `{pnl_val:+.2f}` USDT\n"
                    f"   📅 _{t.timestamp.strftime('%d/%m %H:%M')}_\n\n"
                )

            self.send_message(chat_id, msg)
        except Exception as e:
            logger.error(f"Error in handle_trades: {e}")
            self.send_message(chat_id, f"⚠️ Error al obtener trades: `{str(e)[:150]}`")
        finally:
            db.close()

    def handle_balance(self, chat_id):
        try:
            balances = exchange_service.get_all_balances()
            usdt = next((b for b in balances if b['asset'] == 'USDT'), None)

            if not usdt:
                self.send_message(chat_id, "❌ No se pudo obtener el balance de USDT.")
                return

            free = float(usdt['free'])
            locked = float(usdt['locked'])
            total = free + locked

            msg = (
                f"💰 *Balance en Binance Futures*\n"
                f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                f"💵 *Disponible:* `{free:.2f}` USDT\n"
                f"🔒 *En Posición:* `{locked:.2f}` USDT\n"
                f"📊 *Total:* `{total:.2f}` USDT\n"
            )

            self.send_message(chat_id, msg)
        except Exception as e:
            logger.error(f"Error in handle_balance: {e}")
            self.send_message(chat_id, f"⚠️ Error al obtener balance: `{str(e)[:150]}`")

    def handle_ai_prediction(self, chat_id):
        """Consulta la IA local y devuelve la predicción actual."""
        try:
            response = requests.get("http://127.0.0.1:8000/api/v1/local-ai/predict", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    self.send_message(chat_id, f"🧠 *IA Local*\n\n⚠️ {data['error']}")
                    return

                pred = data.get("prediction", "N/A")
                accuracy = data.get("model_accuracy", 0)
                state = data.get("current_state", {})

                msg = (
                    f"🧠 *PREDICCIÓN IA LOCAL*\n"
                    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                    f"🎯 *Señal:* `{pred}`\n"
                    f"📊 *Precisión:* `{accuracy:.1%}`\n"
                    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                    f"💵 *Precio:* `${state.get('price', 0):.2f}`\n"
                    f"⚡️ *RSI:* `{state.get('rsi', 0):.1f}`\n"
                    f"📏 *ADX:* `{state.get('adx', 0):.1f}`\n"
                    f"🔊 *Volumen:* `{state.get('volume_ratio', 0):.2f}x`\n"
                    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
                    f"📈 Train: `{data.get('train_size', 0)}` | "
                    f"Test: `{data.get('test_size', 0)}`\n"
                )
                self.send_message(chat_id, msg)
            else:
                self.send_message(chat_id, "⚠️ API de IA no disponible.")
        except requests.exceptions.Timeout:
            self.send_message(chat_id, "⏱️ Timeout al consultar la IA. Intenta de nuevo.")
        except Exception as e:
            logger.error(f"Error in handle_ai: {e}")
            self.send_message(chat_id, f"⚠️ Error IA: `{str(e)[:150]}`")

    def handle_help(self, chat_id):
        msg = (
            "❓ *COMANDOS DISPONIBLES*\n"
            "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            "📊 *Estado* — Ver posición actual del bot\n"
            "💰 *Balance* — Consultar fondos en Binance\n"
            "📜 *Últimos Trades* — Historial reciente\n"
            "🧠 *IA Predicción* — Señal de la IA local\n"
            "🆔 *Mi ID* — Ver tu ID de Telegram\n"
            "❓ *Ayuda* — Este menú\n"
        )
        self.send_message(chat_id, msg)

    # ─────────────────────────────────────────────────────────────────────────
    # Message Router
    # ─────────────────────────────────────────────────────────────────────────
    def process_message(self, message):
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = (message.get("text") or "").strip()

        if not chat_id or not text:
            return

        # Security: Only respond to authorized user
        if settings.TELEGRAM_ID != 0 and user_id != settings.TELEGRAM_ID:
            logger.warning(f"Unauthorized access attempt from ID: {user_id}")
            self.send_message(
                chat_id,
                "🛑 *Acceso Denegado.*\nEste bot es privado.",
                show_keyboard=False
            )
            return

        # Normalize: lowercase, strip emoji prefix from button text
        cmd = text.lower().strip()

        # Route commands (supports both button text and /commands)
        if any(kw in cmd for kw in ["/start", "hola", "inicio"]):
            msg = (
                "🤖 *CryptoBot Pro v3.0*\n\n"
                "Bienvenido a tu centro de control.\n"
                "Usa los botones para monitorear tu operativa en tiempo real."
            )
            self.send_message(chat_id, msg)
        elif any(kw in cmd for kw in ["estado", "status", "/status"]):
            self.handle_status(chat_id)
        elif any(kw in cmd for kw in ["trades", "operaciones", "/trades"]):
            self.handle_trades(chat_id)
        elif any(kw in cmd for kw in ["balance", "saldo", "/balance"]):
            self.handle_balance(chat_id)
        elif any(kw in cmd for kw in ["ia", "predicción", "prediccion", "ai", "/ai"]):
            self.handle_ai_prediction(chat_id)
        elif any(kw in cmd for kw in ["id", "/id"]):
            self.send_message(chat_id, f"👤 Tu ID de Telegram es: `{user_id}`")
        elif any(kw in cmd for kw in ["ayuda", "help", "/help"]):
            self.handle_help(chat_id)
        else:
            self.send_message(
                chat_id,
                "🤔 Comando no reconocido. Usa los botones o escribe *Ayuda*."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Polling Loop with Exponential Backoff
    # ─────────────────────────────────────────────────────────────────────────
    def run_polling(self):
        logger.info("Telegram Bot polling started.")

        # Flush any pending updates from before this session to avoid processing old messages
        try:
            flush_url = f"{self.api_url}/getUpdates"
            resp = requests.get(flush_url, params={"offset": -1, "timeout": 1}, timeout=5)
            if resp.status_code == 200:
                results = resp.json().get("result", [])
                if results:
                    self.last_update_id = results[-1]["update_id"]
                    logger.info(f"Flushed {len(results)} old updates. Starting from ID {self.last_update_id + 1}")
        except Exception:
            pass

        self.running = True
        while self.running:
            try:
                updates = self.get_updates()

                for update in updates:
                    update_id = update.get("update_id", self.last_update_id)
                    # Always advance the offset, even if processing fails
                    self.last_update_id = max(self.last_update_id, update_id)

                    if "message" in update:
                        try:
                            self.process_message(update["message"])
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

                # Brief pause between polls to avoid CPU spinning
                time.sleep(0.3)

            except Exception as e:
                self._consecutive_errors += 1
                backoff = min(2 ** self._consecutive_errors, self._max_backoff)
                logger.error(f"Polling error (attempt {self._consecutive_errors}): {e}. Retrying in {backoff:.0f}s...")
                time.sleep(backoff)

        logger.info("Telegram Bot polling stopped.")

    # ─────────────────────────────────────────────────────────────────────────
    # Bot Profile Setup
    # ─────────────────────────────────────────────────────────────────────────
    def setup_bot_profile(self):
        """Configure bot commands and description in Telegram."""
        if not self.token:
            return
        try:
            # Set commands menu
            commands_url = f"{self.api_url}/setMyCommands"
            commands = [
                {"command": "status", "description": "📊 Ver estado del bot"},
                {"command": "balance", "description": "💰 Consultar balance"},
                {"command": "trades", "description": "📜 Historial de trades"},
                {"command": "ai", "description": "🧠 Predicción IA"},
                {"command": "help", "description": "❓ Ver comandos"},
                {"command": "id", "description": "🆔 Ver mi ID"}
            ]
            requests.post(commands_url, json={"commands": commands}, timeout=5)

            # Set bot description
            desc_url = f"{self.api_url}/setMyDescription"
            requests.post(desc_url, json={
                "description": "🤖 CryptoBot Pro v3.0 — Tu asistente de trading automatizado para Binance Futures."
            }, timeout=5)

            logger.info("Bot profile configured successfully.")
        except Exception as e:
            logger.warning(f"Could not set bot profile: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle: Start / Stop with PID-based lock
    # ─────────────────────────────────────────────────────────────────────────
    def _is_lock_stale(self) -> bool:
        """Check if the lock file belongs to a dead process."""
        if not os.path.exists(LOCK_FILE):
            return False
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            # On Windows, check if the process is alive
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
            if handle:
                kernel32.CloseHandle(handle)
                return False  # Process is alive
            return True  # Process is dead
        except (ValueError, OSError, AttributeError):
            # If we can't determine, assume stale
            return True

    def start(self):
        if not self.token:
            logger.warning("No TELEGRAM_TOKEN configured. Telegram bot disabled.")
            return

        # Lock file management with stale detection
        if os.path.exists(LOCK_FILE):
            if self._is_lock_stale():
                logger.info("Removing stale lock file from dead process.")
                try:
                    os.remove(LOCK_FILE)
                except OSError:
                    pass
            else:
                logger.warning("Bot already running (lock file exists and process is alive). Skipping.")
                return

        try:
            with open(LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))

            self._is_active_instance = True
            self.setup_bot_profile()

            self._thread = threading.Thread(target=self.run_polling, daemon=True, name="TelegramBot")
            self._thread.start()
            logger.info(f"Telegram Bot thread launched (PID: {os.getpid()}).")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            self._cleanup_lock()

    def stop(self):
        """Graceful shutdown."""
        logger.info("Stopping Telegram bot...")
        self.running = False
        self._cleanup_lock()

        # Wait for the polling thread to finish (max 5s)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _cleanup_lock(self):
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except OSError:
            pass


# Singleton instance
telegram_bot = TelegramBot()
