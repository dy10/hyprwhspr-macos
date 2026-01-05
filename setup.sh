#!/bin/bash
# whisper-dictate setup script

set -e

echo "=== whisper-dictate Setup ==="
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
VENV_DIR="$HOME/.local/share/whisper-dictate/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    mkdir -p "$HOME/.local/share/whisper-dictate"
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Download Whisper model
echo
echo "Downloading Whisper model (base.en)..."
python3 -c "from pywhispercpp.model import Model; Model('base.en')"

# Create config directory
mkdir -p "$HOME/.config/whisper-dictate"

echo
echo "=== Setup Complete ==="
echo
echo "To run whisper-dictate:"
echo "  source $VENV_DIR/bin/activate"
echo "  python main.py"
echo
echo "IMPORTANT: Grant these permissions in System Preferences:"
echo "  1. Privacy & Security -> Accessibility (for global shortcuts)"
echo "  2. Privacy & Security -> Microphone (for audio recording)"
echo
