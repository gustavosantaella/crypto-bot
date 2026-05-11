from binance.client import Client
import time
from app.core.config import settings

class ExchangeService:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            self.client = Client(
                settings.BINANCE_API_KEY, 
                settings.BINANCE_SECRET_KEY, 
                testnet=settings.IS_TESTNET
            )
            self._sync_time()
        except Exception as e:
            print(f"Error initializing Binance Client: {e}")

    def _sync_time(self):
        if not self.client:
            return
        try:
            server_time = self.client.futures_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
        except Exception as e:
            print(f"Error syncing time: {e}")

    def get_all_balances(self):
        if not self.client:
            self._initialize_client()
        
        if not self.client:
            return []
            
        try:
            balances = self.client.futures_account_balance()
            filtered = []
            for b in balances:
                free = float(b.get('availableBalance', 0))
                total = float(b.get('balance', 0))
                locked = total - free
                if total > 0:
                    filtered.append({
                        "asset": b['asset'],
                        "free": str(free),
                        "locked": str(max(0, locked))
                    })
            return filtered
        except Exception as e:
            print(f"Error in get_all_balances: {e}")
            return []

exchange_service = ExchangeService()
