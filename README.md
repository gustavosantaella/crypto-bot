# Crypto Bot — Spot y Futuros USDT-M (Binance)

Sistema completo de trading automatizado con Binance **spot** y **futuros
USDT-M con apalancamiento**:

| Carpeta   | Descripción                                                          |
|-----------|----------------------------------------------------------------------|
| `bot/`    | Bot en **Python** que lee el precio por WebSocket y opera spot/futuros. |
| `api/`    | **API (FastAPI)** que registra transacciones y órdenes en **MySQL** y calcula la señal de mercado. |
| `portal/` | **Portal web (Angular)** con dashboard, señal LONG/SHORT y transacciones. |

Modos de trading (`TRADE_MODE` en el `.env`):

- **`spot`**    — Estrategia clásica *compra barato / vende caro* (SMA).
- **`futures`** — Estrategia de señal con apalancamiento: abre **LONG** o
  **SHORT** según el score de indicadores (EMA, RSI, MACD, Bollinger) y cierra
  con take-profit, stop-loss o cuando la señal se gira en contra.

El bot ejecuta **una sola operación por ciclo**. Toda la información se reporta
a la API en **segundo plano (hilos)** para no ralentizar el trading.

---

## Arquitectura

```
                         ┌─────────────────────────────┐
   WebSocket Binance     │            bot/             │
   btcusdt@trade ───────▶│ PriceStream (hilo,         │
                         │  reconexión + dedup)        │
                         │      │                      │
                         │      ▼                      │
                         │  TradingState (thread-safe) │
                         │      │                      │
                         │      ▼                      │
                         │  SMAStrategy → decisión     │
                         │      │                      │
                         │      ▼                      │
                         │  TradingEngine              │
                         │   (1 operación/ciclo)       │
                         │      │                      │
                         │  BinanceClient (REST HMAC)  │
                         └──────┬──────────────────────┘
                                │ órdenes ejecutadas
                                ▼
                         ┌─────────────────────────────┐
                         │  ApiReporter (hilo worker)  │  POST/PATCH en
                         │  cola FIFO + retries        │  segundo plano
                         └──────┬──────────────────────┘
                                │
                                ▼
                         ┌─────────────────────────────┐
                         │  api/ (FastAPI) → MySQL     │
                         │  tablas: transactions,      │
                         │  orders                     │
                         └──────────┬──────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────────┐
                         │  portal/ (Angular 20)       │
                         │  dashboard + transacciones  │
                         └─────────────────────────────┘
```

---

## Requisitos

- **Python 3.12+** (probado con 3.14)
- **Node.js 20.19+** (el portal usa Angular 20)
- **MySQL 8** corriendo en `localhost:3306`

## Instalación (1 solo venv + 1 requirements.txt)

El proyecto comparte un **único entorno virtual** y un **único
`requirements.txt`** en la raíz:

```bash
# 1) Crear e instalar el venv único (en la raíz del proyecto)
python -m venv .venv

# Windows
.venv\Scripts\python -m pip install -r requirements.txt
# Linux/macOS
source .venv/bin/python -m pip install -r requirements.txt
```

### Instalar el portal (Angular)

```bash
cd portal
npm install
```

---

## Configuración

### 1. `bot/.env`

```env
TEST_MODE=1                 # 1 = Testnet (virtual), 0 = Producción (real)
TRADE_MODE=spot             # "spot" | "futures"
CURRENCY_TO_USE=BTC
API_URL=http://localhost:8000
BINANCE_WEBSOCKET_URL=wss://stream.binance.com/stream?streams=btcusdt@trade

# --- Parámetros de trading (spot: compra barato / vende caro) ---
QUOTE_AMOUNT=10             # USDT por operación (en futuros: MARGEN)
SMA_PERIOD=20               # Nº de muestras de la ventana de la media móvil
SMA_SAMPLE_MS=400           # Cada cuántos ms se muestrea el precio para la SMA
BUY_THRESHOLD_PCT=0.05      # Comprar si precio <= SMA * (1 - 0.05%)
SELL_PROFIT_PCT=0.05        # Vender si precio >= compra * (1 + 0.05%)
CHECK_INTERVAL_MS=100       # Cada cuánto se evalúa la estrategia
MAX_RECONNECT_DELAY=30      # Backoff máximo (s) del WebSocket
REQUEST_TIMEOUT=5           # Timeout de peticiones REST
```

### Parámetros de futuros (`TRADE_MODE=futures`)

```env
LEVERAGE=3                  # Apalancamiento (nocional = margen * leverage)
MARGIN_TYPE=ISOLATED        # ISOLATED | CROSSED
FUTURES_TAKE_PROFIT_PCT=0.8 # Cerrar con +0.8% de beneficio (sobre la entrada)
FUTURES_STOP_LOSS_PCT=0.4   # Cerrar con -0.4% de pérdida (stop-loss duro)
SIGNAL_OPEN_SCORE=1.5       # Abrir LONG/SHORT si |score| >= este valor
SIGNAL_CLOSE_SCORE=0.5      # Cerrar si la señal se gira (|score| <= valor)
KLINE_INTERVAL=1m           # Velas para los indicadores
KLINE_LIMIT=300             # Nº de velas históricas
ANALYSIS_REFRESH_MS=15000   # Refresco del análisis por REST

# --- Indicadores (RSI / MACD / EMA) ---
RSI_PERIOD=14
RSI_OVERSOLD=30
RSI_OVERBOUGHT=70
EMA_FAST=12
EMA_SLOW=26
EMA_SIGNAL=9
EMA_TREND_FAST=50
EMA_TREND_SLOW=200
```

#### Modo pruebas vs. producción

`TEST_MODE=1` **activa automáticamente la Testnet de Binance** (endpoints y
sockets de prueba) y `TRADE_MODE` elige entre spot y futuros:

| Recurso   | Mercado  | TEST_MODE=1 (testnet)                        | TEST_MODE=0 (real)            |
|-----------|----------|----------------------------------------------|-------------------------------|
| REST      | spot     | `https://testnet.binance.vision`             | `https://api.binance.com`     |
| REST      | futuros  | `https://testnet.binancefuture.com`          | `https://fapi.binance.com`    |
| WebSocket | spot     | `wss://stream.testnet.binance.vision/stream` | `wss://stream.binance.com/stream` |
| WebSocket | futuros  | `wss://stream.testnet.binancefuture.com/stream` | `wss://fstream.binance.com/stream` |

La URL del `.env` define **qué streams escuchar** (`streams=btcusdt@trade`);
el bot conserva ese stream y solo cambia el host según el modo y entorno.

> ⚠️ **Las API keys de la Testnet de SPOT se generan gratis en
> https://testnet.binance.vision/** y las de **FUTUROS en
> https://testnet.binancefuture.com/** (son distintas). Si defines
> `BINANCE_API_KEY_FUTURES`/`BINANCE_SECRET_KEY_FUTURES`, el bot las usará en
> modo futuros; si no, hará fallback a las de spot (y Binance las rechazará en
> la testnet de futuros con error de autenticación).

### 2. `api/.env`

```env
DB_HOST=localhost
DB_USER=root
DB_PASS=root
DB_NAME=cryptobot

TEST_MODE=1
TRADE_MODE=spot             # "spot" | "futures" (mercado por defecto en la API)
LEVERAGE=3                  # Apalancamiento (se muestra en el portal)
CURRENCY_TO_USE=BTC

# Credenciales de SPOT (testnet y producción)
BINANCE_API_KEY_TEST=...
BINANCE_SECRET_KEY_TEST=...
BINANCE_API_KEY_PROD=...
BINANCE_SECRET_KEY_PROD=...

# Credenciales de FUTUROS (opcionales; fallback a las de spot)
BINANCE_API_KEY_TEST_FUTURES=...
BINANCE_SECRET_KEY_TEST_FUTURES=...
BINANCE_API_KEY_PROD_FUTURES=...
BINANCE_SECRET_KEY_PROD_FUTURES=...

# Análisis de mercado (señal LONG/SHORT/NEUTRAL)
KLINE_INTERVAL=1m
KLINE_LIMIT=300
ANALYSIS_REFRESH_MS=15000
```

La API crea automáticamente la base de datos y las tablas al arrancar
(`transactions` y `orders`). Si ya existían, se ejecutan **migraciones ligeras**
que añaden los campos de futuros (`market_type`, `side`, `leverage`, margen,
liquidación, TP/SL...) sin tocar las filas antiguas de spot. El balance se
consulta en la **testnet** o en **producción** según `test_mode` y en spot o
futuros según `market_type` (parámetro de `GET /api/balance`).

---

## Cómo ejecutar

### 1) API (independiente del bot)

```bash
cd api
..\.venv\Scripts\python main.py      # Windows
# o equivalente en tu SO. Alternativa: uvicorn app.main:app --port 8000
```

La API queda en `http://localhost:8000` (documentación interactiva en
`/docs`). El bot **solo hace peticiones** a esta API; no la arranca.

### 2) Bot

```bash
cd bot
..\.venv\Scripts\python main.py
```

El bot (modo **spot**):
1. Se conecta al WebSocket de Binance (testnet o real según `TEST_MODE`).
2. Llena la ventana de la media móvil (SMA) con los primeros ticks.
3. Cuando el precio cae por debajo de `SMA * (1 - BUY_THRESHOLD_PCT%)`,
   **compra** `QUOTE_AMOUNT` USDT al mercado.
4. Cuando el precio sube hasta `compra * (1 + SELL_PROFIT_PCT%)`, **vende**
   toda la posición.
5. Cada compra/venta se registra en la API en segundo plano.

En modo **futuros** (`TRADE_MODE=futures`) el bot:
1. Aplica el apalancamiento y el tipo de margen configurados (`LEVERAGE`,
   `MARGIN_TYPE`) al símbolo.
2. Siembra velas históricas (klines) y las actualiza en tiempo real con el
   stream de trades.
3. Calcula el score de indicadores (EMA 50/200, RSI, MACD, Bollinger) cada
   ciclo y abre **LONG** si `score >= SIGNAL_OPEN_SCORE` o **SHORT** si
   `score <= -SIGNAL_OPEN_SCORE`.
4. Cierra la posición con take-profit, stop-loss o cuando la señal se gira.
5. Al arrancar, recupera la posición abierta real desde `positionRisk` de
   Binance (si el bot se reinició con una operación abierta).

Detén el bot con `Ctrl+C` (apaga el stream y espera a que la cola de
reportes se vacíe).

### 3) Portal (Angular)

```bash
cd portal
npm start        # ng serve --proxy-config proxy.conf.json
```

Abre **http://localhost:4200**. En desarrollo, `/api` se proxya hacia
`http://localhost:8000` (sin problemas de CORS).

---

## Estrategias de trading

### Spot — comprar barato, vender caro (SMA)

1. Se mantiene una ventana deslizante con los últimos `SMA_PERIOD` precios.
2. **COMPRA** cuando `precio_actual <= SMA * (1 - BUY_THRESHOLD_PCT/100)`.
   El precio cayó por debajo del promedio reciente → se considera barato.
3. **VENTA** cuando `precio_actual >= precio_compra * (1 + SELL_PROFIT_PCT/100)`.
   Solo se vende **por encima** del precio de compra.

### Futuros — señal LONG/SHORT (score de indicadores)

El bot calcula un **score compuesto** (rango ≈ -6..+6) a partir de velas:

| Indicador         | Contribución al score                                   |
|-------------------|---------------------------------------------------------|
| Precio vs EMA50   | +1 por encima / -1 por debajo                           |
| EMA50 vs EMA200   | +1 estructura alcista / -1 bajista                      |
| RSI(14)           | +1 sobrevendido (<30), -1 sobrecomprado (>70), escala continua |
| MACD histograma   | +1 alcista / -1 bajista                                 |
| Cruce MACD        | +0.5 cruce alcista / -0.5 bajista                       |
| Bollinger         | +0.5 bajo banda inferior / -0.5 sobre banda superior    |

- **Abrir LONG** cuando `score >= SIGNAL_OPEN_SCORE`.
- **Abrir SHORT** cuando `score <= -SIGNAL_OPEN_SCORE`.
- **Cerrar** por take-profit (`FUTURES_TAKE_PROFIT_PCT`), stop-loss
  (`FUTURES_STOP_LOSS_PCT`) o cuando el score se gira en contra.

La **señal de mercado** también se expone vía `GET /api/analysis/signal`
(con recomendación LONG/SHORT/NEUTRAL, RSI, MACD, funding rate...) y se
publica en vivo por SSE (`market.analysis`) para el portal.

> ⚠️ Los indicadores ayudan a decidir, pero **ninguna estrategia garantiza
> rentabilidad**. En futuros el apalancamiento amplifica tanto ganancias como
> pérdidas: usa stop-loss y prueba siempre primero en la Testnet.

## Robusteza / concurrencia

| Problema                          | Solución implementada                                                |
|-----------------------------------|----------------------------------------------------------------------|
| Los trades llegan **muy rápido**  | `TradingState` guarda el **último trade id** y descarta duplicados.   |
| Dobles órdenes por error          | Flag `order_in_flight` bajo `threading.Lock` + evaluación cada `CHECK_INTERVAL_MS`. |
| 2 compras sin vender              | `is_busy()` bloquea compras mientras haya posición abierta o orden en vuelo. |
| La API lentifica el trading       | `ApiReporter` envía todo en **hilos de background** (cola FIFO + retries). |
| La venta sin ganancia             | La estrategia exige `precio >= compra * (1 + margen)` para vender.    |
| Venta rechazada por `minNotional` | La compra se ajusta al step size y garantiza notional >= mínimo (nunca quedas con una posición invendible). |
| Caída del WebSocket               | `PriceStream` reconecta con **backoff exponencial** (1s, 2s, 4s… máx. `MAX_RECONNECT_DELAY`) indefinidamente. |
| Reloj local desincronizado        | El cliente sincroniza su reloj con `GET /api/v3/time` (offset) al arrancar. |
| La SMA no detecta caídas          | La SMA se construye con **muestreo temporal** (`SMA_SAMPLE_MS`) en vez de por-trade, para reflejar un periodo real. |
| Orden parcial/fallida             | Se valida `status == FILLED` y `executedQty > 0` antes de actualizar el estado. |

### ¿Qué pasa si mato el bot con una operación abierta?

La posición vive en memoria; al matar el bot se pierde, pero la transacción
queda `OPEN` en la API y el activo (BTC) sigue en la cuenta spot. Al **reiniciar**,
el bot ejecuta una **reconciliación automática**:

1. Consulta las transacciones `OPEN` en la API.
2. Consulta el balance spot real de Binance.
3. Si el BTC sigue en la cuenta → **recupera la posición** y continúa el ciclo
   (venderá cuando el precio suba).
4. Si el BTC ya no está (o la cantidad no cuadra) → **cancela** la transacción
   (`CANCELED`).

### Balance spot y ganancias/pérdidas

- La **API** consulta el balance de la cuenta spot de Binance (`GET /api/balance`)
  usando las credenciales de `api/.env` (claves `_TEST` y `_PROD` para cada
  ambiente).
- El **portal** tiene un **switch en el sidebar** (TESTNET ⇄ PRODUCCIÓN) que
  selecciona el ambiente a visualizar: balance spot, stats, transacciones y
  órdenes se filtran automáticamente. Es solo visualización, no afecta al bot.
- Las stats separan ganancias/pérdidas por ambiente (`wins_*`, `losses_*`,
  `total_profit_*`).

### Hilos del bot

| Hilo                 | Qué hace                                                        |
|----------------------|-----------------------------------------------------------------|
| `PriceStream`        | Recibe ticks del WebSocket y actualiza el precio (daemon).      |
| `ApiReporter` worker | Consume la cola y hace POST/PATCH a la API (daemon).            |
| `main` (engine)      | Evalúa la estrategia y ejecuta órdenes de forma síncrona.       |


---

## Modelo de datos (MySQL)

Tabla principal **`transactions`** — un ciclo compra → venta por fila:

| Campo           | Tipo            | Descripción                                    |
|-----------------|-----------------|------------------------------------------------|
| `id`            | BIGINT          | Clave primaria                                 |
| `symbol`        | VARCHAR(20)     | Par, ej. `BTCUSDT`                             |
| `status`        | ENUM            | `OPEN` (comprado, sin vender) / `CLOSED` / `CANCELED` |
| `test_mode`     | BOOL            | **1 = registro de prueba (testnet), 0 = real** |
| `buy_order_id`  | BIGINT          | Orden de compra en Binance                     |
| `buy_price`     | DECIMAL(30,10)  | Precio medio de compra                         |
| `buy_quantity`  | DECIMAL(30,10)  | Cantidad comprada                              |
| `buy_quote`     | DECIMAL(30,10)  | USDT gastados                                  |
| `buy_time`      | DATETIME        | **Cuándo se compró**                           |
| `sell_order_id` | BIGINT          | Orden de venta en Binance                      |
| `sell_price`    | DECIMAL(30,10)  | Precio medio de venta                          |
| `sell_quantity` | DECIMAL(30,10)  | Cantidad vendida                               |
| `sell_quote`    | DECIMAL(30,10)  | USDT recibidos                                 |
| `sell_time`     | DATETIME        | **Cuándo se vendió**                           |
| `profit`        | DECIMAL(30,10)  | **Ganancia en USDT** (`sell_quote - buy_quote`)|
| `profit_pct`    | DECIMAL(12,6)   | Rentabilidad porcentual                        |
| `created_at`/`updated_at` | DATETIME | Marcas de auditoría                       |

Tabla auxiliar **`orders`**: auditoría de cada orden enviada a Binance
(par, lado BUY/SELL, `binance_order_id`, precio, cantidad, estado, `test_mode`).

## Endpoints de la API

| Método | Ruta                              | Descripción                                    |
|--------|-----------------------------------|------------------------------------------------|
| GET    | `/health`                         | Estado de la API                               |
| POST   | `/api/transactions`               | Crear transacción (el bot al comprar)          |
| PATCH  | `/api/transactions/{id}`          | Cerrar transacción (el bot al vender)          |
| POST   | `/api/transactions/{id}/cancel`   | Cancelar una OPEN huérfana (reconciliación)    |
| GET    | `/api/transactions`               | Listar (`?test_mode=`, `?status=`, `limit`, `offset`) |
| GET    | `/api/transactions/{id}`          | Detalle                                        |
| GET    | `/api/transactions/stats`         | Resumen + ganancia/pérdida por ambiente (TEST/REAL) |
| POST   | `/api/orders`                     | Registrar una orden (auditoría)                |
| GET    | `/api/orders`                     | Listar órdenes                                 |
| GET    | `/api/balance`                    | Balance (y posiciones de futuros) de Binance   |
| GET    | `/api/analysis/signal`            | Señal de mercado LONG/SHORT/NEUTRAL            |
| GET    | `/api/events`                     | **SSE**: eventos en tiempo real (compra/venta, precio, señal) |

### Actualizaciones en tiempo real (SSE)

Cuando el bot registra una compra/venta/cancelación, la API publica un evento
**SSE** (`text/event-stream`) que el portal consume con `EventSource` y
actualiza el dashboard, la lista y el detalle **sin recargar la página**:

```
GET /api/events
event: transaction.created     ← el bot abrió posición (compra)
event: transaction.updated     ← el bot cerró posición (venta)
event: transaction.canceled    ← se canceló una OPEN huérfana
event: market.analysis         ← señal de mercado recalculada
```

Incluye un *heartbeat* cada 15 s para mantener la conexión viva, y el
`EventSource` del navegador se reconecta automáticamente si se cae.

### Precio en vivo (SSE)

La API también se conecta a los **WebSockets de precios de Binance** (testnet
y producción, ambos públicos) al arrancar, y publica el precio cada ~2 s:

```
event: price
data: {"test_mode": true, "symbol": "BTCUSDT", "price": 77397.42, "time": ...}
```

El **sidebar del portal** muestra el precio en vivo del ambiente seleccionado
en el switch (TESTNET o PRODUCCIÓN).

### Señal de mercado (SSE)

Un hilo interno recalcula la señal (klines → indicadores → score) cada
`ANALYSIS_REFRESH_MS` ms para spot y futuros, y publica `market.analysis`:

```
event: market.analysis
data: {"market_type": "FUTURES", "recommendation": "SHORT", "score": -2.8,
       "indicators": {"rsi14": 31.2, "macd_hist": -0.4, "ema50": 79000, ...},
       "funding_rate": 0.0001, "summary": "..."}
```

El dashboard muestra la recomendación, el score, el RSI, el MACD y la
tendencia en vivo.

---

## Validación

Con la API corriendo (`cd api && python main.py`) y el venv de la raíz:

```bash
# Test de integración del bot (feed simulado, sin operar en Binance)
.venv\Scripts\python bot\test_integration.py
```

Este test inyecta precios sintéticos, comprueba que el bot **compra barato,
vende caro, obtiene ganancia** y que **la API registra el ciclo en MySQL**
(crear + cerrar).

> Los scripts `validate_bot.py` y `test_integration.py` son herramientas de
> desarrollo y se pueden borrar en producción.

---

## Estructura del proyecto

```
crypto-bot/
├── requirements.txt          # Deps únicas (bot + api) — un solo venv
├── .venv/                    # Entorno virtual único
├── README.md
├── bot/
│   ├── .env                  # Credenciales y parámetros (TRADE_MODE, LEVERAGE...)
│   ├── main.py               # Punto de entrada
│   ├── config.py             # Carga .env y deriva URLs spot/futuros testnet/real
│   ├── demo_trade.py         # Demo: apertura+cierre real en testnet
│   └── app/
│       ├── binance_client.py # REST Binance (HMAC) spot /api/v3 + futuros /fapi/v1
│       ├── price_stream.py   # WebSocket con reconexión + backoff
│       ├── state.py          # Estado thread-safe (precio, posición, velas, dedup)
│       ├── strategy.py       # SMAStrategy (spot) + FuturesStrategy (LONG/SHORT)
│       ├── indicators.py     # RSI, MACD, EMA, Bollinger, ATR, score compuesto
│       ├── candle_buffer.py  # Velas OHLC desde klines + stream de trades
│       ├── engine.py         # Motor: 1 operación/ciclo + reconciliación
│       ├── api_client.py     # Consultas síncronas a la API (arranque)
│       ├── api_reporter.py   # Envío a la API en background (cola + retry)
│       └── models.py         # Dataclasses (Position, FilledOrder, MarketAnalysis...)
├── api/
│   ├── .env                  # MySQL + credenciales de Binance (spot y futuros)
│   ├── main.py               # Launcher independiente de la API
│   └── app/
│       ├── main.py           # App FastAPI (incluye routers + emitter de señal)
│       ├── config.py         # Settings desde api/.env
│       ├── database.py       # SQLAlchemy + PyMySQL + create DB
│       ├── migrations.py     # ALTER TABLE para campos de futuros (no rompe spot)
│       ├── models.py         # Entidades transactions y orders (SPOT/FUTURES)
│       ├── schemas.py        # Schemas Pydantic
│       ├── binance.py        # Cliente balance/posiciones (HMAC) spot + fapi
│       ├── analysis.py       # Señal de mercado (klines → score LONG/SHORT)
│       ├── analysis_emitter.py  # Hilo SSE que publica market.analysis
│       ├── price_stream.py   # WebSocket de precios → SSE
│       ├── events.py         # Bus de eventos en memoria (SSE)
│       └── routers/
│           ├── transactions.py
│           ├── orders.py
│           ├── balance.py    # balance + posiciones de futuros
│           ├── analysis.py   # GET /api/analysis/signal
│           └── events.py     # GET /api/events (SSE)
└── portal/
    ├── proxy.conf.json       # /api → localhost:8000 en dev
    ├── angular.json
    └── src/
        ├── environments/     # apiUrl por entorno
        └── app/
            ├── core/         # modelos + servicios HTTP (transactions, balance, señal)
            ├── shared/       # pipes y componentes reutilizables
            └── features/
                ├── dashboard/       # señal LONG/SHORT + balance spot/futuros + stats + tabla
                └── transactions/    # listado con filtros (mercado/estado) + detalle
```

---

## Advertencias

- Este proyecto es educativo. **Operar con dinero real implica riesgo.**
  Empieza siempre en `TEST_MODE=1`.
- La estrategia SMA es básica y no asegura rentabilidad en ningún mercado.
- La Testnet de Binance se **resetea periódicamente** (fondos y órdenes
  vuelven a cero).
- No uses las API keys de producción en la Testnet ni al revés.

