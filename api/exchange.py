from binance.client import Client
import os
import time
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
IS_TESTNET_STR = os.getenv("IS_TESTNET", "True")
IS_TESTNET = IS_TESTNET_STR == "True"
print(f"DEBUG: Loading IS_TESTNET as {IS_TESTNET} (from string '{IS_TESTNET_STR}')")
print(f"DEBUG: API_KEY: {BINANCE_API_KEY[:5] if BINANCE_API_KEY else 'NONE'}...")
print(f"DEBUG: SECRET_KEY: {BINANCE_SECRET_KEY[:5] if BINANCE_SECRET_KEY else 'NONE'}...")

class ExchangeManager:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            self.client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=IS_TESTNET)
            self._sync_time()
            print(f"Binance Client initialized and synced successfully (Testnet: {IS_TESTNET})")
        except Exception as e:
            print(f"Error initializing Binance Client: {e}")

    def _sync_time(self):
        if not self.client:
            return
        try:
            server_time = self.client.futures_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
            print(f"DEBUG: Time synced (Futures). Offset: {self.client.timestamp_offset}ms")
        except Exception as e:
            print(f"DEBUG: Error syncing time: {e}")

    def get_all_balances(self):
        if not self.client:
            self._initialize_client()
        
        if not self.client:
            return []
            
        try:
            # En Futuros usamos futures_account_balance
            balances = self.client.futures_account_balance()
            filtered = []
            for b in balances:
                # Keys en Binance Futures: asset, balance, availableBalance, etc.
                free = float(b.get('availableBalance', 0))
                total = float(b.get('balance', 0))
                locked = total - free
                if total > 0:
                    filtered.append({
                        "asset": b['asset'],
                        "free": str(free),
                        "locked": str(max(0, locked))
                    })
            print(f"DEBUG: Found {len(filtered)} futures assets with balance > 0")
            return filtered
        except Exception as e:
            print(f"DEBUG: Error in get_all_balances (Futures): {e}")
            return []

    def get_asset_balance(self, asset):
        if not self.client:
            self._initialize_client()
            
        if not self.client:
            return {"asset": asset, "free": "0", "locked": "0"}
        try:
            balances = self.client.futures_account_balance()
            for b in balances:
                if b['asset'] == asset:
                    free = float(b.get('availableBalance', 0))
                    total = float(b.get('balance', 0))
                    locked = total - free
                    return {"asset": asset, "free": str(free), "locked": str(max(0, locked))}
            return {"asset": asset, "free": "0", "locked": "0"}
        except Exception as e:
            return {"asset": asset, "free": "0", "locked": "0"}
