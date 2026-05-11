# Símbolo de trading (Par de criptomonedas a operar)
SYMBOL = 'SOLUSDT'

# Porcentaje del balance disponible (USDT) a usar por operación (0.0 a 1.0)
# Ejemplo: 0.8 significa usar el 80% del USDT disponible
TRADE_PERCENTAGE = 0.5

# Configuración del Indicador RSI
RSI_PERIOD = 14      # Número de periodos para el cálculo del RSI
RSI_OVERSOLD = 35    # Nivel de sobreventa (Subido de 30 para ser más activo pero seguro)
RSI_OVERBOUGHT = 65  # Nivel de sobrecompra (Bajado de 70 para asegurar ganancias más rápido)

# Gestión de Riesgo (Risk Management)
STOP_LOSS_PCT = 0.03    # Porcentaje de pérdida máxima (3%) antes de cerrar la posición
TAKE_PROFIT_PCT = 0.05  # Porcentaje de ganancia objetivo (5%) para cerrar la posición

# Intervalo de revisión del bot en segundos
CHECK_INTERVAL = 10
