/** Modelo de una transacción (ciclo compra → venta) registrado por el bot. */
export type TransactionStatus = 'OPEN' | 'CLOSED' | 'CANCELED';

export interface Transaction {
  id: number;
  symbol: string;
  status: TransactionStatus;
  test_mode: boolean;

  // --- Compra ---
  buy_order_id: number | null;
  buy_price: number;
  buy_quantity: number;
  buy_quote: number;
  buy_time: string;

  // --- Venta ---
  sell_order_id: number | null;
  sell_price: number | null;
  sell_quantity: number | null;
  sell_quote: number | null;
  sell_time: string | null;

  // --- Resultado ---
  profit: number | null;
  profit_pct: number | null;

  created_at: string;
  updated_at: string;
}
