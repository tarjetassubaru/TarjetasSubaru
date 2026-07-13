#!/bin/bash
set -x

echo "=== Starting CreditoSubaru ==="
echo "Running migration..."
python migrate_neon.py 2>&1 || echo "MIGRATION FAILED WITH EXIT CODE: $?"

echo "Running seed..."
python seed.py 2>&1 || echo "SEED FAILED WITH EXIT CODE: $?"

echo "Starting API and bot..."
# Start API in background
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &

# Start Telegram bot
python bot.py &

# Keep container alive
wait
