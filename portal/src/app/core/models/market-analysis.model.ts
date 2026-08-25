import { MarketType } from './transaction.model';

export type Recommendation = 'LONG' | 'SHORT' | 'NEUTRAL';
export type Trend = 'bullish' | 'bearish' | 'neutral';

/** Indicadores técnicos calculados por el backend. */
export interface MarketIndicators {
  sma20: number | null;
  ema50: number | null;
  ema200: number | null;
  rsi14: number | null;
  rsi_oversold: number;
  rsi_overbought: number;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_middle: number | null;
  atr14: number | null;
  score: number;
  components: Record<string, number>;
  trend: Trend;
}

/** Señal de mercado devuelta por GET /api/analysis/signal. */
export interface MarketAnalysis {
  market_type: MarketType;
  test_mode: boolean;
  symbol: string;
  price: number;
  interval: string;
  change_24h_pct: number | null;
  funding_rate: number | null;
  mark_price: number | null;
  index_price: number | null;
  next_funding_time?: number;
  volume?: number;
  indicators: MarketIndicators;
  trend: Trend;
  score: number;
  recommendation: Recommendation;
  confidence_pct: number;
  summary: string;
  time: number;
}
