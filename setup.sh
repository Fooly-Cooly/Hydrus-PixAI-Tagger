#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "=== Hydrus PixAI Tagger Setup ==="

# 1. Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# 2. Activate Venv
source venv/bin/activate

# 3. Install Dependencies
echo "Installing/Upgrading Python dependencies..."
pip install --upgrade pip
pip install torch torchvision transformers pillow PyQt6 hydrus-api

# 4. Make run script executable
chmod +x run.sh

echo ""
echo "Setup complete! You can now launch the application by running ./run.sh"