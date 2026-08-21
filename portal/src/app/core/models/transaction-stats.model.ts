/** Resumen estadístico devuelto por GET /api/transactions/stats. */
export interface TransactionStats {
  total: number;
  open: number;
  closed: number;
  test_mode: number;
  real: number;
  total_profit: number;
  avg_profit: number;
  // Ganancia/pérdida separada por ambiente (TEST_MODE).
  total_profit_test: number;
  total_profit_real: number;
  wins_test: number;
  losses_test: number;
  wins_real: number;
  losses_real: number;
}
