import sys
import os

# Añadir la raíz del proyecto al path para que reconozca el paquete src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.exchange import ExchangeManager
from src.config.settings import IS_TESTNET

def main():
    print("========================================")
    print(f"   CONSULTA DE SALDO ({'TESTNET' if IS_TESTNET else 'REAL'})")
    print("========================================")
    
    try:
        exchange = ExchangeManager()
        # Obtenemos todos los balances de la cuenta
        account_info = exchange.client.get_account()
        balances = account_info.get('balances', [])
        
        found = False
        for asset_balance in balances:
            free = float(asset_balance['free'])
            locked = float(asset_balance['locked'])
            total = free + locked
            
            if total > 0:
                print(f"🔸 {asset_balance['asset']}:")
                print(f"   Disponible: {free}")
                print(f"   Bloqueado:  {locked}")
                print(f"   Total:      {total}")
                print("-" * 20)
                found = True
        
        if not found:
            print("No se encontraron activos con saldo mayor a cero.")
            
    except Exception as e:
        print(f"Error al consultar saldo: {e}")

if __name__ == "__main__":
    main()
