#!/bin/bash
# Start API in background
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &

# Start Telegram bot
python bot.py &

# Keep container alive
wait
