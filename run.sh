#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Check if venv exists in /tmp/venv
if [ -f "/tmp/venv/bin/uvicorn" ]; then
    VENV_PY="/tmp/venv/bin/python"
    UVICORN_BIN="/tmp/venv/bin/uvicorn"
elif [ -d "$DIR/.venv" ]; then
    VENV_PY="$DIR/.venv/bin/python"
    UVICORN_BIN="$DIR/.venv/bin/uvicorn"
else
    echo "Creating virtual environment..."
    python3 -m venv /tmp/venv
    /tmp/venv/bin/pip install -r requirements.txt
    VENV_PY="/tmp/venv/bin/python"
    UVICORN_BIN="/tmp/venv/bin/uvicorn"
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "=========================================================="
echo " Starting FRED + Gemini Economic Assistant on http://${HOST}:${PORT}"
echo "=========================================================="

export PYTHONPATH="$DIR"
exec "$UVICORN_BIN" app.main:app --host "$HOST" --port "$PORT" --reload
