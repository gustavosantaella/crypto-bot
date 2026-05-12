#!/bin/bash

# Este script se llama a sí mismo con parámetros para abrir terminales separadas

if [ "$1" == "portal" ]; then
    echo "🖥️ Iniciando Portal (Angular)..."
    cd portal && npm start
    echo "Portal cerrado. Presiona Enter para salir..."
    read
    exit
fi

if [ "$1" == "api" ]; then
    echo "🔌 Iniciando API (Uvicorn)..."
    cd api && source ../.venv/Scripts/activate && python run.py
    echo "API cerrada. Presiona Enter para salir..."
    read
    exit
fi

if [ "$1" == "bot" ]; then
    echo "🤖 Iniciando Bot..."
    cd bot && source ../.venv/Scripts/activate && python run.py
    echo "Bot cerrado. Presiona Enter para salir..."
    read
    exit
fi

# Si no hay argumentos, lanzar las tres terminales
echo "🚀 Iniciando servicios de Crypto Bot..."

# Obtenemos la ruta absoluta del script para que las nuevas terminales lo encuentren
SCRIPT_PATH=$(readlink -f "$0")

start bash "$SCRIPT_PATH" portal
start bash "$SCRIPT_PATH" api
start bash "$SCRIPT_PATH" bot

echo "✅ Todos los servicios han sido lanzados en terminales separadas."
