/** Modelo de una transacción (ciclo compra→venta / apertura→cierre). */
export type TransactionStatus = 'OPEN' | 'CLOSED' | 'CANCELED';
export type MarketType = 'SPOT' | 'FUTURES';
export type PositionSide = 'LONG' | 'SHORT';

export interface Transaction {
  id: number;
  symbol: string;
  status: TransactionStatus;
  test_mode: boolean;

  /** Identifica si el registro proviene de spot o de futuros. */
  market_type: MarketType;
  /** Dirección de la posición: LONG (compra) o SHORT (venta, solo futuros). */
  side: PositionSide;
  /** Apalancamiento aplicado (1 en spot). */
  leverage: number;

  // --- Compra / apertura ---
  buy_order_id: number | null;
  buy_price: number;
  buy_quantity: number;
  buy_quote: number;
  buy_time: string;

  // --- Venta / cierre ---
  sell_order_id: number | null;
  sell_price: number | null;
  sell_quantity: number | null;
  sell_quote: number | null;
  sell_time: string | null;

  // --- Resultado ---
  profit: number | null;
  profit_pct: number | null;

  // --- Futuros (null en spot) ---
  notional: number | null;
  margin: number | null;
  liquidation_price: number | null;
  take_profit_price: number | null;
  stop_loss_price: number | null;

  created_at: string;
  updated_at: string;
}

