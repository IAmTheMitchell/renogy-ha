#!/bin/bash
set -e

# 0. Set WSL hostname to wsl-ha-dev if not already set
if [ "$(hostname)" != "wsl-ha-dev" ]; then
  echo "Setting WSL hostname to wsl-ha-dev (requires sudo)..."
  echo "wsl-ha-dev" | sudo tee /etc/hostname
  sudo sed -i 's/127.0.1.1.*/127.0.1.1\twsl-ha-dev/' /etc/hosts
  sudo hostname wsl-ha-dev
  echo "Hostname changed. Please restart your WSL instance for changes to take full effect."
fi

echo "1. Resetting to latest upstream/main..."
git fetch upstream
git reset --hard upstream/main

echo "2. Cleaning untracked files and directories..."
git clean -fdx

echo "3. Recreating Python virtual environment..."
rm -rf .venv

# 4. Ensure uv is installed
if ! command -v uv &> /dev/null; then
  echo "uv not found, installing..."
  pip install uv || curl -sSf https://astral.sh/uv/install.sh | sh
fi

uv venv
source .venv/bin/activate

echo "5. Installing dependencies..."
uv pip install -r requirements.txt

echo "6. Running test suite..."
uv run pytest tests

echo "7. Checking Home Assistant integration loads (manual step):"
echo "   - Start Home Assistant and check logs for errors."
echo "   - Confirm at least one Renogy device is detected."

echo "8. Ready for new integration work!"

# Reminder: Run this script from outside your project, or re-copy it in after cleaning.
