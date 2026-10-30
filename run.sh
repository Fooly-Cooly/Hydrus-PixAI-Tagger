#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# If venv doesn't exist, trigger first-time setup
if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Starting setup installer..."
    echo ""
    bash "$SCRIPT_DIR/setup.sh"
    if [ ! -d "venv" ]; then
        echo ""
        echo "[ERROR] Setup was cancelled or failed. Cannot start application."
        exit 1
    fi
    echo ""
fi

echo "Starting Hydrus PixAI Tagger..."
python3 "$SCRIPT_DIR/hydrus_pixai_tagger.py" "$@"
