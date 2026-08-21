# Crypto Bot — Compra barato, vende caro (Binance Spot)

Sistema completo de trading automatizado en **spot** con Binance:

| Carpeta   | Descripción                                                          |
|-----------|----------------------------------------------------------------------|
| `bot/`    | Bot en **Python** que lee el precio por WebSocket y compra/vende.     |
| `api/`    | **API (FastAPI)** que registra las transacciones en **MySQL**.       |
| `portal/` | **Portal web (Angular)** para visualizar las transacciones.          |

El bot ejecuta **una sola operación por ciclo**: si ya compró, no vuelve a
comprar hasta que venda la posición. La venta **solo se dispara por encima
del precio de compra** (ganancia positiva garantizada por estrategia), y toda
la información se reporta a la API en **segundo plano (hilos)** para no
ralentizar el trading.

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
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key
TEST_MODE=1
CURRENCY_TO_USE=BTC
API_URL=http://localhost:8000
BINANCE_WEBSOCKET_URL=wss://stream.binance.com/stream?streams=btcusdt@trade

# --- Parámetros de trading ---
QUOTE_AMOUNT=10          # USDT invertidos en cada compra (>= minNotional)
SMA_PERIOD=20            # Nº de muestras de la ventana de la media móvil
SMA_SAMPLE_MS=500        # Cada cuántos ms se muestrea el precio para la SMA
                         # (500ms => la SMA cubre los últimos 10 s)
BUY_THRESHOLD_PCT=0.05   # Comprar si precio <= SMA * (1 - 0.05%)
SELL_PROFIT_PCT=0.05     # Vender si precio >= compra * (1 + 0.05%)
CHECK_INTERVAL_MS=500    # Cada cuánto se evalúa la estrategia
MAX_RECONNECT_DELAY=30   # Backoff máximo (s) del WebSocket
REQUEST_TIMEOUT=5        # Timeout de peticiones REST
```

#### Modo pruebas vs. producción

`TEST_MODE=1` **activa automáticamente la Testnet de Binance** (endpoints y
sockets de prueba):

| Recurso    | TEST_MODE=1 (testnet)            | TEST_MODE=0 (real)          |
|------------|----------------------------------|-----------------------------|
| REST       | `https://testnet.binance.vision` | `https://api.binance.com`   |
| WebSocket  | `wss://stream.testnet.binance.vision/stream` | `wss://stream.binance.com/stream` |

La URL del `.env` define **qué streams escuchar** (`streams=btcusdt@trade`);
el bot conserva ese stream y solo cambia el host según el modo.

> ⚠️ **Las API keys de la Testnet se generan gratis en
> https://testnet.binance.vision/** (los fondos son virtuales). Las keys de
> producción **no** funcionan contra la testnet (error `-2015`). Para operar
> en real, pon las keys de tu cuenta de Binance y `TEST_MODE=0`.

### 2. `api/.env`

```env
DB_HOST=localhost
DB_USER=root
DB_PASS=root
DB_NAME=cryptobot

# Credenciales de Binance (copiadas de bot/.env): se usan para consultar el
# balance de la cuenta spot desde la API (GET /api/balance).
TEST_MODE=1
CURRENCY_TO_USE=BTC
BINANCE_API_KEY=tu_api_key
BINANCE_SECRET_KEY=tu_secret_key
```

La API crea automáticamente la base de datos y las tablas al arrancar
(`transactions` y `orders`). `TEST_MODE` debe coincidir con el del bot: la
API consulta el balance en la **testnet** o en **producción** según ese valor.

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

El bot:
1. Se conecta al WebSocket de Binance (testnet o real según `TEST_MODE`).
2. Llena la ventana de la media móvil (SMA) con los primeros ticks.
3. Cuando el precio cae por debajo de `SMA * (1 - BUY_THRESHOLD_PCT%)`,
   **compra** `QUOTE_AMOUNT` USDT al mercado.
4. Cuando el precio sube hasta `compra * (1 + SELL_PROFIT_PCT%)`, **vende**
   toda la posición.
5. Cada compra/venta se registra en la API en segundo plano.

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

## Estrategia de trading

**Comprar barato, vender caro** usando la media móvil simple (SMA) como
precio de referencia:

1. Se mantiene una ventana deslizante con los últimos `SMA_PERIOD` precios.
2. **COMPRA** cuando `precio_actual <= SMA * (1 - BUY_THRESHOLD_PCT/100)`.
   El precio cayó por debajo del promedio reciente → se considera barato.
3. **VENTA** cuando `precio_actual >= precio_compra * (1 + SELL_PROFIT_PCT/100)`.
   Solo se vende **por encima** del precio de compra → ganancia garantizada
   por la condición (la ganancia real se calcula con los precios de
   ejecución reales de Binance).

## Robusteza / concurrencia

| Problema                          | Solución implementada                                                |
|-----------------------------------|----------------------------------------------------------------------|
| Los trades llegan **muy rápido**  | `TradingState` guarda el **último trade id** y descarta duplicados.   |
| Dobles órdenes por error          | Flag `order_in_flight` bajo `threading.Lock` + evaluación cada `CHECK_INTERVAL_MS`. |
| 2 compras sin vender              | `is_busy()` bloquea compras mientras haya posición abierta o orden en vuelo. |
| La API lentifica el trading       | `ApiReporter` envía todo en **hilos de background** (cola FIFO + retries). |
| La venta sin ganancia             | La estrategia exige `precio >= compra * (1 + margen)` para vender.    |
| Caída del WebSocket               | `PriceStream` reconecta con **backoff exponencial** (1s, 2s, 4s… máx. `MAX_RECONNECT_DELAY`) indefinidamente. |
| Reloj local desincronizado        | El cliente sincroniza su reloj con `GET /api/v3/time` (offset) al arrancar. |
| Orden parcial/fallida             | Se valida `status == FILLED` y `executedQty > 0` antes de actualizar el estado. |

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
| GET    | `/api/transactions`               | Listar (`?test_mode=`, `?status=`, `limit`, `offset`) |
| GET    | `/api/transactions/{id}`          | Detalle                                        |
| GET    | `/api/transactions/stats`         | Resumen (totales, ganancia)                    |
| POST   | `/api/orders`                     | Registrar una orden (auditoría)                |
| GET    | `/api/orders`                     | Listar órdenes                                 |

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
│   ├── .env                  # Credenciales y parámetros
│   ├── main.py               # Punto de entrada
│   ├── config.py             # Carga .env y deriva URLs testnet/real
│   └── app/
│       ├── binance_client.py # REST Binance (HMAC-SHA256)
│       ├── price_stream.py   # WebSocket con reconexión + backoff
│       ├── state.py          # Estado thread-safe (precio, posición, dedup)
│       ├── strategy.py       # SMA: comprar barato / vender caro
│       ├── engine.py         # Motor: 1 operación por ciclo
│       ├── api_reporter.py   # Envío a la API en background (cola + retry)
│       └── models.py         # Dataclasses (Position, FilledOrder, ...)
├── api/
│   ├── .env                  # Credenciales MySQL
│   ├── main.py               # Launcher independiente de la API
│   └── app/
│       ├── main.py           # App FastAPI (incluye routers)
│       ├── config.py         # Settings desde api/.env
│       ├── database.py       # SQLAlchemy + PyMySQL + create DB
│       ├── models.py         # Entidades transactions y orders
│       ├── schemas.py        # Schemas Pydantic
│       └── routers/
│           ├── transactions.py
│           └── orders.py
└── portal/
    ├── proxy.conf.json       # /api → localhost:8000 en dev
    ├── angular.json
    └── src/
        ├── environments/     # apiUrl por entorno
        └── app/
            ├── core/         # modelos + servicios HTTP
            ├── shared/       # pipes y componentes reutilizables
            └── features/
                ├── dashboard/       # stats + últimas transacciones
                └── transactions/    # listado con filtros + detalle
```

---

## Advertencias

- Este proyecto es educativo. **Operar con dinero real implica riesgo.**
  Empieza siempre en `TEST_MODE=1`.
- La estrategia SMA es básica y no asegura rentabilidad en ningún mercado.
- La Testnet de Binance se **resetea periódicamente** (fondos y órdenes
  vuelven a cero).
- No uses las API keys de producción en la Testnet ni al revés.

