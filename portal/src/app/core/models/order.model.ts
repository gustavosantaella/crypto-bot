/** Modelo de una orden individual enviada a Binance (auditoría). */
export type OrderSide = 'BUY' | 'SELL';

export interface Order {
  id: number;
  transaction_id: number | null;
  symbol: string;
  side: OrderSide;
  binance_order_id: number;
  price: number;
  quantity: number;
  quote_quantity: number;
  status: string;
  test_mode: boolean;
  created_at: string;
}
