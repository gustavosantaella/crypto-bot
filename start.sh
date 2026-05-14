#!/bin/bash

# ==============================================================================
# CryptoBot Launcher - Professional Edition
# ==============================================================================
# Uso:
#   ./start.sh          : Inicia (o reinicia) todos los servicios.
#   ./start.sh -b       : Inicia solo el Bot.
#   ./start.sh -a       : Inicia solo la API (FastAPI).
#   ./start.sh --env=sol: Inicia usando el entorno solana (.sol.env).
#   ./start.sh --bye    : Mata todos los procesos y cierra el lanzador.
# ==============================================================================

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PIDS_DIR="$(cd "$(dirname "$0")" && pwd)/.pids"
mkdir -p "$PIDS_DIR"

# ── Funciones de Limpieza y Control de Procesos ───────────────────────────────

kill_port() {
    local port="$1"
    local name="$2"
    local pids=$(netstat -ano 2>/dev/null | awk -v port=":${port}" '$0 ~ port && /LISTENING/ {print $5}' | sort -u)
    for pid in $pids; do
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            echo -e "${YELLOW}    ⚠️  Forzando cierre de $name en puerto $port (PID: $pid)...${NC}"
            taskkill //F //PID "$pid" >/dev/null 2>&1
        fi
    done
}

kill_service() {
    local name="$1"
    local pidfile="$PIDS_DIR/$2"

    if [ -f "$pidfile" ]; then
        local shell_pid=$(cat "$pidfile" 2>/dev/null)
        rm -f "$pidfile"

        if [ -n "$shell_pid" ]; then
            echo -e "${YELLOW}    🔪 Cerrando terminal de $name (PID: $shell_pid)...${NC}"
            # Matar el árbol de procesos para asegurar cierre de terminales
            taskkill //F //T //PID "$shell_pid" >/dev/null 2>&1
            kill -9 "$shell_pid" 2>/dev/null
        fi
    fi
}

cleanup_locks() {
    rm -f "api/bot.lock" 2>/dev/null
}

# ── Ejecutores para las ventanas hijas ────────────────────────────────────────

if [ "$1" == "portal_exec" ]; then
    cat /proc/self/winpid > "$PIDS_DIR/portal.pid" 2>/dev/null
    echo -e "${BLUE}🖥️  Iniciando Portal (Angular)...${NC}"
    cd portal || exit
    if [ ! -d "node_modules" ]; then
        echo "Instalando dependencias (npm install)..."
        npm install
    fi
    npm start
    rm -f "$PIDS_DIR/portal.pid"
    echo -e "${RED}Portal cerrado. Presiona Enter para salir...${NC}"
    read -r
    exit
fi

if [ "$1" == "api_exec" ]; then
    cat /proc/self/winpid > "$PIDS_DIR/api.pid" 2>/dev/null
    echo -e "${GREEN}🔌 Iniciando API (Uvicorn)...${NC}"
    cd api || exit
    if [ ! -d "../.venv" ]; then
        echo -e "${RED}Error: No se encontró el entorno virtual .venv${NC}"
        read -r
        exit 1
    fi
    ENV_FLAG=""
    if [ -n "$2" ]; then ENV_FLAG="--env=$2"; fi
    source ../.venv/Scripts/activate && python run.py $ENV_FLAG
    rm -f "$PIDS_DIR/api.pid"
    echo -e "${RED}API cerrada. Presiona Enter para salir...${NC}"
    read -r
    exit
fi

if [ "$1" == "bot_exec" ]; then
    cat /proc/self/winpid > "$PIDS_DIR/bot.pid" 2>/dev/null
    echo -e "${GREEN}🤖 Iniciando Bot de Trading...${NC}"
    cd bot || exit
    if [ ! -d "../.venv" ]; then
        echo -e "${RED}Error: No se encontró el entorno virtual .venv${NC}"
        read -r
        exit 1
    fi
    ENV_FLAG=""
    if [ -n "$2" ]; then ENV_FLAG="--env=$2"; fi
    source ../.venv/Scripts/activate && python run.py $ENV_FLAG
    rm -f "$PIDS_DIR/bot.pid"
    echo -e "${RED}Bot cerrado. Presiona Enter para salir...${NC}"
    read -r
    exit
fi

# ── Acción --bye: Matar todo y salir ──────────────────────────────────────────

if [ "$1" == "--bye" ]; then
    echo -e "\n${RED}═══════════════════════════════════════════════${NC}"
    echo -e "${RED}  💀 CryptoBot — Apagando todo el sistema${NC}"
    echo -e "${RED}═══════════════════════════════════════════════${NC}\n"

    kill_service "API"    "api.pid"
    kill_service "Portal" "portal.pid"
    kill_service "Bot"    "bot.pid"
    kill_port 8000 "API"
    kill_port 4200 "Portal"
    cleanup_locks
    rm -f "$PIDS_DIR"/*.pid 2>/dev/null

    echo -e "\n${GREEN}  ✅ Todos los procesos y terminales cerrados exitosamente.${NC}\n"
    exit 0
fi

# ── Lógica Principal de Lanzamiento ───────────────────────────────────────────

START_BOT=false
START_PORTAL=false
START_API=false
SPECIFIC_SERVICE=false

for arg in "$@"; do
    case $arg in
        -b) START_BOT=true; SPECIFIC_SERVICE=true ;;
        -p) START_PORTAL=true; SPECIFIC_SERVICE=true ;;
        -a) START_API=true; SPECIFIC_SERVICE=true ;;
        --env=*) ENV_ARG="${arg#*=}" ;;
        *)  echo -e "${RED}Argumento inválido: $arg${NC}"; exit 1 ;;
    esac
done

if [ "$SPECIFIC_SERVICE" = false ]; then
    START_BOT=true
    START_PORTAL=true
    START_API=true
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  🚀 CryptoBot Launcher Pro${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"

echo "🔍 Preparando entorno y limpiando procesos previos..."

if [ "$START_API" = true ]; then
    kill_service "API" "api.pid"
    kill_port 8000 "API"
fi

if [ "$START_PORTAL" = true ]; then
    kill_service "Portal" "portal.pid"
    kill_port 4200 "Portal"
fi

if [ "$START_BOT" = true ]; then
    kill_service "Bot" "bot.pid"
    cleanup_locks
fi

sleep 1 # Dar tiempo a que se liberen los puertos

echo -e "\n✨ Iniciando servicios seleccionados..."
SCRIPT_PATH=$(readlink -f "$0")

if [ "$START_PORTAL" = true ]; then
    echo -e "${BLUE}  → Levantando Portal (Angular) en puerto 4200...${NC}"
    start bash "$SCRIPT_PATH" portal_exec
fi

if [ "$START_API" = true ]; then
    echo -e "${GREEN}  → Levantando API (FastAPI) en puerto 8000...${NC}"
    start bash "$SCRIPT_PATH" api_exec "$ENV_ARG"
fi

if [ "$START_BOT" = true ]; then
    echo -e "${GREEN}  → Levantando Bot (Trading Engine)...${NC}"
    start bash "$SCRIPT_PATH" bot_exec "$ENV_ARG"
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Servicios iniciados correctamente.${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}\n"
