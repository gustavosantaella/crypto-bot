/** Resumen estadístico devuelto por GET /api/transactions/stats. */
export interface TransactionStats {
  total: number;
  open: number;
  closed: number;
  test_mode: number;
  real: number;
  total_profit: number;
  avg_profit: number;
}
