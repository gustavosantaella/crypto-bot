#!/bin/bash

# Este script puede recibir parámetros:
# -b: Inicia el Bot
# -p: Inicia el Portal
# -a: Inicia la API
# Si no recibe nada, inicia los tres.

# Lógica interna para las ventanas hijas
if [ "$1" == "portal_exec" ]; then
    echo "🖥️ Iniciando Portal (Angular)..."
    cd portal && npm start
    echo "Portal cerrado. Presiona Enter para salir..."
    read
    exit
fi

if [ "$1" == "api_exec" ]; then
    echo "🔌 Iniciando API (Uvicorn)..."
    cd api && source ../.venv/Scripts/activate && python run.py
    echo "API cerrada. Presiona Enter para salir..."
    read
    exit
fi

if [ "$1" == "bot_exec" ]; then
    echo "🤖 Iniciando Bot..."
    cd bot && source ../.venv/Scripts/activate && python run.py
    echo "Bot cerrado. Presiona Enter para salir..."
    read
    exit
fi

# --- Lógica del Lanzador Principal ---
START_BOT=false
START_PORTAL=false
START_API=false

if [ $# -eq 0 ]; then
    # Por defecto, todos
    START_BOT=true
    START_PORTAL=true
    START_API=true
else
    # Parsear flags
    for arg in "$@"; do
        case $arg in
            -b) START_BOT=true ;;
            -p) START_PORTAL=true ;;
            -a) START_API=true ;;
        esac
    done
fi

echo "🚀 Iniciando servicios seleccionados..."
SCRIPT_PATH=$(readlink -f "$0")

if [ "$START_PORTAL" = true ]; then
    echo "Lanzando Portal..."
    start bash "$SCRIPT_PATH" portal_exec
fi

if [ "$START_API" = true ]; then
    echo "Lanzando API..."
    start bash "$SCRIPT_PATH" api_exec
fi

if [ "$START_BOT" = true ]; then
    echo "Lanzando Bot..."
    start bash "$SCRIPT_PATH" bot_exec
fi

echo "✅ Proceso de inicio completado."
