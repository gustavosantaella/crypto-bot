#!/bin/bash

# Este script puede recibir parámetros:
# -b: Inicia el Bot
# -p: Inicia el Portal
# -a: Inicia la API
# --bye: Mata todos los procesos, cierra las terminales y sale
# Si no recibe nada, inicia los tres.

PIDS_DIR="$(cd "$(dirname "$0")" && pwd)/.pids"

# ── Matar proceso por puerto (Windows: netstat + taskkill) ────────────────────
kill_port() {
    local port="$1"
    local name="$2"
    local pids=$(netstat -ano 2>/dev/null | grep ":${port}" | grep "LISTENING" | awk '{print $5}' | sort -u)
    for pid in $pids; do
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            echo "    ⚠️  Matando $name en puerto $port (PID: $pid)"
            taskkill //F //PID "$pid" 2>/dev/null
        fi
    done
}

# ── Matar un servicio por su .pid file + cerrar su terminal ───────────────────
kill_service() {
    local name="$1"
    local pidfile="$PIDS_DIR/$2"

    if [ ! -f "$pidfile" ]; then
        return
    fi

    local shell_pid=$(cat "$pidfile" 2>/dev/null)
    rm -f "$pidfile"

    if [ -z "$shell_pid" ]; then
        return
    fi

    echo "    🔪 Cerrando terminal de $name (PID: $shell_pid)"

    # 1. Matar todos los procesos hijos del bash (python, node, npm, etc.)
    #    En Windows/MSYS, usamos taskkill con /T (tree kill) para matar el
    #    proceso y todos sus hijos de una vez, lo que cierra la terminal.
    taskkill //F //T //PID "$shell_pid" 2>/dev/null

    # 2. Fallback: kill directo por si taskkill no lo alcanzó
    kill -9 "$shell_pid" 2>/dev/null
}

# ── Matar todos los servicios y cerrar sus terminales ─────────────────────────
kill_all_services() {
    echo "🔍 Buscando procesos activos..."

    # Matar por PID file (cierra las terminales)
    kill_service "API"    "api.pid"
    kill_service "Portal" "portal.pid"
    kill_service "Bot"    "bot.pid"

    # Fallback: matar por puerto si quedaron huérfanos
    kill_port 8000 "API"
    kill_port 4200 "Portal"

    sleep 1
}

# ── Limpiar lock files huérfanos ──────────────────────────────────────────────
cleanup_locks() {
    rm -f "api/bot.lock" 2>/dev/null
}

cleanup_pids() {
    rm -f "$PIDS_DIR"/*.pid 2>/dev/null
}

# ══════════════════════════════════════════════════════════════════════════════
# Lógica interna para las ventanas hijas
# Cada ventana guarda su PID ($$) en un archivo .pid para que el launcher
# pueda encontrarla y matarla (junto con la terminal) al reiniciar o --bye.
# ══════════════════════════════════════════════════════════════════════════════
if [ "$1" == "portal_exec" ]; then
    mkdir -p "$PIDS_DIR"
    cat /proc/self/winpid > "$PIDS_DIR/portal.pid"
    echo "🖥️ Iniciando Portal (Angular)..."
    cd portal && npm start
    rm -f "$PIDS_DIR/portal.pid"
    echo "Portal cerrado. Presiona Enter para salir..."
    read
    exit
fi

if [ "$1" == "api_exec" ]; then
    mkdir -p "$PIDS_DIR"
    cat /proc/self/winpid > "$PIDS_DIR/api.pid"
    echo "🔌 Iniciando API (Uvicorn)..."
    cd api && source ../.venv/Scripts/activate && python run.py
    rm -f "$PIDS_DIR/api.pid"
    echo "API cerrada. Presiona Enter para salir..."
    read
    exit
fi

if [ "$1" == "bot_exec" ]; then
    mkdir -p "$PIDS_DIR"
    cat /proc/self/winpid > "$PIDS_DIR/bot.pid"
    echo "🤖 Iniciando Bot..."
    cd bot && source ../.venv/Scripts/activate && python run.py
    rm -f "$PIDS_DIR/bot.pid"
    echo "Bot cerrado. Presiona Enter para salir..."
    read
    exit
fi

# ══════════════════════════════════════════════════════════════════════════════
# --bye: Matar todo, cerrar terminales, salir
# ══════════════════════════════════════════════════════════════════════════════
if [ "$1" == "--bye" ]; then
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  💀 CryptoBot — Apagando todo"
    echo "═══════════════════════════════════════════════"
    echo ""

    kill_all_services
    cleanup_locks
    cleanup_pids

    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ✅ Todos los procesos y terminales cerrados"
    echo "═══════════════════════════════════════════════"
    echo ""
    exit 0
fi

# ══════════════════════════════════════════════════════════════════════════════
# Lanzador Principal
# ══════════════════════════════════════════════════════════════════════════════
START_BOT=false
START_PORTAL=false
START_API=false

if [ $# -eq 0 ]; then
    START_BOT=true
    START_PORTAL=true
    START_API=true
else
    for arg in "$@"; do
        case $arg in
            -b) START_BOT=true ;;
            -p) START_PORTAL=true ;;
            -a) START_API=true ;;
        esac
    done
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  🚀 CryptoBot Launcher"
echo "═══════════════════════════════════════════════"
echo ""

# ── Paso 1: Matar procesos y terminales anteriores ────────────────────────────
kill_all_services
cleanup_locks

# ── Paso 2: Iniciar servicios en nuevas terminales ────────────────────────────
echo ""
echo "✨ Iniciando servicios..."
SCRIPT_PATH=$(readlink -f "$0")

if [ "$START_PORTAL" = true ]; then
    echo "  → Portal (Angular) en puerto 4200"
    start bash "$SCRIPT_PATH" portal_exec
fi

if [ "$START_API" = true ]; then
    echo "  → API (FastAPI/Uvicorn) en puerto 8000"
    start bash "$SCRIPT_PATH" api_exec
fi

if [ "$START_BOT" = true ]; then
    echo "  → Bot (Trading Engine)"
    start bash "$SCRIPT_PATH" bot_exec
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ Todos los servicios lanzados"
echo "═══════════════════════════════════════════════"
echo ""
