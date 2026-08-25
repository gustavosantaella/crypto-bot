import { MarketType } from './transaction.model';

/** Balance de un activo en la cuenta de Binance (spot o futuros). */
export interface AssetBalance {
  asset: string;
  free: number;
  locked: number;
  // Futuros:
  margin_balance?: number;
  wallet_balance?: number;
  unrealized_profit?: number;
}

/** Posición abierta en futuros (GET /api/balance con market_type=FUTURES). */
export interface FuturesPosition {
  symbol: string;
  side: 'LONG' | 'SHORT';
  position_amt: number;
  entry_price: number;
  mark_price: number;
  notional: number;
  unrealized_profit: number;
  profit_pct: number;
  liquidation_price: number | null;
  leverage: number;
  margin_type: string;
  margin_ratio: number;
}

/** Respuesta de GET /api/balance. */
export interface AccountBalance {
  test_mode: boolean;
  market_type: MarketType;
  symbol: string;
  currency: string;
  leverage: number;
  balances: AssetBalance[];
  positions: FuturesPosition[];
}

