/** Balance de un activo en la cuenta spot de Binance. */
export interface AssetBalance {
  asset: string;
  free: number;
  locked: number;
}

/** Respuesta de GET /api/balance. */
export interface AccountBalance {
  test_mode: boolean;
  symbol: string;
  currency: string;
  balances: AssetBalance[];
}
