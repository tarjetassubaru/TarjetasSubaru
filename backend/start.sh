#!/bin/bash
# Start API in background
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &

# Start Telegram bot with auto-restart on crash
while true; do
    echo "Starting bot..."
    python bot.py
    echo "Bot crashed, restarting in 3s..."
    sleep 3
done &

# Keep container alive
wait
