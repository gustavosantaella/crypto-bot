"""
ai_trainer.py — Background AI Training & Prediction Logger

Runs in a background thread alongside the bot engine.
Every TRAIN_INTERVAL seconds, it:
  1. Queries the local AI endpoint for a fresh train + predict cycle
  2. Logs the prediction, accuracy, and market state to logs/ia.log
  3. Caches the latest prediction for the bot engine to read

The ia.log file serves as a historical record of all AI predictions,
enabling offline analysis of model performance over time.
"""

import time
import threading
import logging
import os
import json
import requests
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
TRAIN_INTERVAL = 120        # Seconds between AI train/predict cycles (2 min)
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

# ── IA Logger Setup ───────────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
ia_logger = logging.getLogger("IATrainer")
ia_logger.setLevel(logging.INFO)
ia_logger.propagate = False  # Don't duplicate to root logger

# File handler → ia.log
_ia_handler = logging.FileHandler(os.path.join(LOG_DIR, "ia.log"), encoding="utf-8")
_ia_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
ia_logger.addHandler(_ia_handler)

# Also log errors to console
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter("%(asctime)s [IA] %(message)s"))
ia_logger.addHandler(_console_handler)


class AITrainer:
    """
    Background AI trainer that periodically re-trains the KNN model
    and logs predictions to ia.log for historical analysis.
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._running = False

        # Cached prediction (read by bot_engine.py)
        self.prediction: str = "HOLD 😐"
        self.accuracy: float = 0.0
        self.raw_prediction: int = 0
        self.last_train_time: float = 0.0
        self.train_count: int = 0
        self.consecutive_errors: int = 0

    def start(self):
        """Launch the background training thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._training_loop,
            daemon=True,
            name="AITrainer"
        )
        self._thread.start()
        ia_logger.info("=" * 60)
        ia_logger.info("  AI Background Trainer Started")
        ia_logger.info(f"  Train interval: {TRAIN_INTERVAL}s")
        ia_logger.info(f"  API URL: {API_URL}")
        ia_logger.info("=" * 60)

    def stop(self):
        """Signal the training loop to stop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        ia_logger.info("AI Background Trainer stopped.")

    def _training_loop(self):
        """Main loop: train → predict → log → sleep → repeat."""
        # Initial delay to let the API start up
        time.sleep(15)

        while self._running:
            try:
                self._train_and_predict()
                self.consecutive_errors = 0
            except Exception as e:
                self.consecutive_errors += 1
                ia_logger.error(f"Training cycle failed (attempt {self.consecutive_errors}): {e}")

                # Backoff on consecutive errors
                if self.consecutive_errors > 5:
                    backoff = min(60 * self.consecutive_errors, 600)  # Max 10 min
                    ia_logger.warning(f"Too many errors. Backing off for {backoff}s...")
                    time.sleep(backoff)

            time.sleep(TRAIN_INTERVAL)

    def _train_and_predict(self):
        """
        Calls the local AI endpoint to trigger a full train+predict cycle.
        Logs the complete result to ia.log.
        """
        start_time = time.time()

        # Call the API with different look-ahead values for a more robust prediction
        results = {}
        for look_ahead in [3, 5, 10]:
            try:
                response = requests.get(
                    f"{API_URL}/local-ai/predict",
                    params={"look_ahead": look_ahead, "k": 5},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    if "error" not in data:
                        results[look_ahead] = data
            except requests.exceptions.Timeout:
                ia_logger.warning(f"Timeout calling AI for look_ahead={look_ahead}")
            except Exception as e:
                ia_logger.warning(f"Error calling AI for look_ahead={look_ahead}: {e}")

        if not results:
            ia_logger.warning("No predictions obtained from any look-ahead window.")
            return

        elapsed = time.time() - start_time
        self.train_count += 1
        self.last_train_time = time.time()

        # Use the primary prediction (look_ahead=5) if available, else fallback
        primary = results.get(5) or results.get(3) or list(results.values())[0]
        self.prediction = primary.get("prediction", "HOLD 😐")
        self.accuracy = primary.get("model_accuracy", 0.0)
        self.raw_prediction = primary.get("raw_prediction", 0)

        state = primary.get("current_state", {})

        # Build consensus across look-ahead windows
        votes = {}
        for la, res in results.items():
            raw = res.get("raw_prediction", 0)
            signal_map = {1: "LONG", -1: "SHORT", 0: "HOLD"}
            label = signal_map.get(raw, "HOLD")
            votes[f"LA{la}"] = label

        # Log detailed prediction
        ia_logger.info(
            f"[PREDICCIÓN] {self.prediction} | "
            f"Precisión: {self.accuracy:.1%} | "
            f"Precio: ${state.get('price', 0):.2f} | "
            f"RSI: {state.get('rsi', 0):.1f} | "
            f"ADX: {state.get('adx', 0):.1f} | "
            f"Vol: {state.get('volume_ratio', 0):.2f}x | "
            f"Consenso: {votes} | "
            f"Train #{self.train_count} ({elapsed:.1f}s)"
        )

        # Log detailed metrics for analysis
        for la, res in results.items():
            neighbor_votes = res.get("neighbors_votes", {})
            ia_logger.info(
                f"  └─ LA{la}: {res.get('prediction', 'N/A')} | "
                f"Acc: {res.get('model_accuracy', 0):.1%} | "
                f"Train: {res.get('train_size', 0)} | "
                f"Test: {res.get('test_size', 0)} | "
                f"Votes: {neighbor_votes}"
            )

        # Consensus signal (majority vote)
        raw_votes = [r.get("raw_prediction", 0) for r in results.values()]
        from collections import Counter
        consensus_raw = Counter(raw_votes).most_common(1)[0][0]
        signal_map = {1: "LONG 🚀", -1: "SHORT 📉", 0: "HOLD 😐"}
        consensus_signal = signal_map.get(consensus_raw, "HOLD 😐")

        if consensus_signal != self.prediction:
            ia_logger.info(
                f"  ⚠️ Consenso difiere de predicción principal: "
                f"{consensus_signal} vs {self.prediction}"
            )

    def get_cached_prediction(self) -> dict:
        """Returns the cached prediction for the bot engine to use."""
        return {
            "prediction": self.prediction,
            "accuracy": self.accuracy,
            "raw_prediction": self.raw_prediction,
            "last_train_time": self.last_train_time,
            "train_count": self.train_count
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
ai_trainer = AITrainer()
