/** Modelo de una orden individual enviada a Binance (auditoría). */
export type OrderSide = 'BUY' | 'SELL';
export type MarketType = 'SPOT' | 'FUTURES';

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
  market_type: MarketType;
  position_side: string | null;
  leverage: number;
  created_at: string;
}

