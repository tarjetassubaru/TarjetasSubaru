#!/bin/bash
# Start API in background
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &

# Start Telegram bot (single instance, no loop)
python bot.py &
