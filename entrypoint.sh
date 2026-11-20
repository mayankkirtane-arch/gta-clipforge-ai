#!/bin/bash
set -e

echo "🚀 Starting GTA ClipForge AI Backend on port 8000..."
cd /app/backend
python run.py &
BACKEND_PID=$!

echo "🚀 Starting GTA ClipForge AI Frontend on port ${PORT:-10000}..."
cd /app/frontend
export PORT=${PORT:-10000}
export HOSTNAME="0.0.0.0"
node server.js &
FRONTEND_PID=$!

# Wait for any process to exit
wait -n $BACKEND_PID $FRONTEND_PID
