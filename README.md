# 🤖 Crypto Bot — Estrategia DCA con Parámetros Adaptativos (SOLUSDT)

¡Bienvenido al panel de control y motor de trading automatizado para Binance Futures! Este proyecto opera **SOLUSDT** en temporalidad de 1 Hora usando una estrategia de **DCA (Dollar Cost Averaging)** con **parámetros dinámicos que se adaptan al estado del mercado en tiempo real**.

---

## 📚 Conceptos Básicos (Para Principiantes)

### 1. ¿Qué son los Futuros?
A diferencia de comprar cripto normal (Spot), en **Futuros** firmas un contrato sobre el precio:
*   **Apalancamiento (`3x`):** Operas con 3 veces más capital del que tienes. Amplifica ganancias **y** pérdidas.
*   **Puedes ganar en ambas direcciones:** El bot puede apostar a que el precio sube o baja.

### 2. LONG vs SHORT
*   **LONG:** Compras esperando que el precio **suba**.
*   **SHORT:** Vendes esperando que el precio **baje**.

### 3. Los Indicadores (Los ojos del bot)
*   **RSI:** Mide si la moneda está "barata" (sobrevendida, RSI < 30) o "cara" (sobrecomprada, RSI > 68). El umbral de entrada **se ajusta dinámicamente** según el ADX.
*   **EMA 200:** Línea de tendencia macro (promedio de 200 horas). El bot solo abre LONGs si el precio está **0.3% o más arriba** de la EMA200.
*   **ATR:** Mide la volatilidad del momento. Con ATR alto, el bot da más espacio al SL y TP. Con ATR bajo, los ajusta más.
*   **ADX:** Fuerza de la tendencia. Es la clave del sistema dinámico.

---

## ⚙️ El Sistema de Parámetros Dinámicos

Esta es la principal innovación del bot. En lugar de usar valores fijos, el módulo `parameter_adapter.py` calcula en **cada ciclo** los parámetros óptimos basados en el ADX:

| Estado del ADX | Mercado | Acción del Bot |
|---|---|---|
| `ADX < 20` | **Lateral / Sin tendencia** | RSI sube +5 (más oportunidades), DCA más cercano (-20%) |
| `ADX 20–25` | **Neutral / Zona gris** | Usa valores base del `.env` sin cambios |
| `ADX > 25` | **Tendencia activa** | RSI baja -5 (más exigente), SL y DCA más amplios (+30%) |

Esto garantiza que el bot **no se quede dormido en mercados tranquilos** y al mismo tiempo **no entre a ciegas en tendencias fuertes**.

Puedes ver el modo activo en cada línea de log:
```
[SOLUSDT] P: 90.96 | RSI: 17.0 | ADX: 28.5 | ... | Mode: CONSERVATIVE/TRENDING | RSI_umbral: 25
```

---

## 🔀 Modos de Operación (BOT_MODE)

Cambia el modo editando `bot/.env` → `BOT_MODE=` y reiniciando el bot.

| Modo | Perfil | Descripción |
|---|---|---|
| `CONSERVATIVE` | 🛡️ Bajo riesgo | Menos operaciones, ganancias más grandes. Parámetros adaptativos activos. |
| `SCALPING` | ⚡ Alta frecuencia | Muchas operaciones, ganancias pequeñas y frecuentes. RSI=35, TP=1.0x ATR. |

---

## 🛠️ Cómo Funciona la Estrategia (Paso a Paso)

### 1. Condiciones de Entrada LONG (todas deben cumplirse)
1.  **RSI < umbral dinámico** (entre 25–35, calculado por el adaptador)
2.  **Precio > EMA200 × 1.003** (0.3% sobre la EMA, mercado alcista)
3.  **Sin tendencia bajista fuerte** (ADX no confirma caída sostenida con DI-)

### 2. El Método DCA
*   **Entrada 1:** Primera compra.
*   **Entrada 2:** Si el precio cae **2.5%** y RSI baja a **25** → compra más.
*   **Entrada 3:** Si el precio cae más y RSI llega a **20** → compra la última porción.

*Cada entrada reduce el precio promedio, necesitando menos rebote para estar en positivo.*

### 3. Gestión de Riesgo
*   **Take Profit (TP):** `avg_price + (ATR × 3.5)` — dinámico según volatilidad.
*   **Stop Loss (SL):** `avg_price - (ATR × 2.5)` — protección siempre activa.
*   **Cleanup de órdenes:** Elimina automáticamente órdenes antiguas o duplicadas en Binance.
*   **Trailing Stop (Breakeven):** Si el precio sube 1.5 ATR desde la entrada, mueve el SL al precio de entrada → nunca pierdes en un trade que estuvo en verde.

---

## 📁 Estructura del Proyecto

```text
crytpto-bot/
├── README.md               # ← Este archivo
├── start.sh                # Script de inicio unificado
├── requirements.txt        # Dependencias Python
│
├── bot/                    # 🧠 Motor del Bot (Python)
│   ├── .env                # ⚙️ Configuración y credenciales
│   └── src/
│       ├── core/
│       │   ├── bot_engine.py      # Ciclo principal del bot
│       │   └── exchange.py        # Conexión y órdenes con Binance API
│       ├── strategies/
│       │   ├── rsi_strategy.py    # Lógica de señales (BUY/SELL/HOLD)
│       │   └── parameter_adapter.py  # 🆕 Adaptador dinámico de parámetros
│       ├── config/
│       │   └── trading_params.py  # Carga de variables del .env
│       └── utils/
│           ├── logger.py          # Logger con colores en consola
│           ├── db.py              # Base de datos local
│           └── telegram_notifier.py # Notificaciones Telegram
│
├── api/                    # 🌐 Backend (FastAPI)
│   └── # Comunica el bot con la interfaz web via WebSocket
│
└── portal/                 # 💻 Frontend (Angular)
    └── src/app/
        └── pages/dashboard/ # Panel principal con gráficas y trades
```

---

## 🚀 Cómo Iniciar

```bash
# Iniciar solo el bot en segundo plano
bash start.sh -b

# Iniciar todo (Bot + API + Portal)
bash start.sh
```

---

## 🛠️ Configuración `.env` — Valores Actuales

```env
BOT_MODE=CONSERVATIVE       # CONSERVATIVE o SCALPING
SYMBOL=SOLUSDT
LEVERAGE=3
RSI_OVERSOLD=30             # Umbral BASE (el adaptador lo modifica por ADX)
RSI_OVERBOUGHT=68
ATR_SL_MULTIPLIER=2.5       # Multiplicador BASE del SL (dinámico)
ATR_TP_MULTIPLIER=3.5       # Multiplicador BASE del TP (dinámico)
DCA_MIN_DROP_PCT=0.025      # Caída mínima BASE para DCA (dinámica)
DCA_RSI_LEVEL_2=25          # RSI para 2da entrada DCA
DCA_RSI_LEVEL_3=20          # RSI para 3ra entrada DCA
MAX_DCA_ORDERS=3            # Máximo de entradas DCA
USE_TRAILING_STOP=True      # Breakeven automático
```

---

## 🎨 Sistema de Logs con Colores

El bot imprime logs con colores en la terminal para facilitar el monitoreo:

*   🟢 **[INFO]** — Actividad normal del bot (señales, ciclos).
*   🟡 **[WARNING]** — Situaciones que merecen atención (balance bajo, ajustes).
*   🔴 **[ERROR]** — Fallos de API o errores de ejecución.
*   🟣 **[CRITICAL]** — Errores fatales que requieren intervención inmediata.

---
*Documentación actualizada — Bot con parámetros adaptativos y modos de operación múltiples.*
