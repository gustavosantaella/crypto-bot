import os
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
IS_TESTNET = os.getenv('IS_TESTNET', 'True') == 'True' # Cambiar a False para real
