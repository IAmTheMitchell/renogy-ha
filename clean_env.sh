#!/bin/bash
set -e
<<<<<<< HEAD
export UV_LINK_MODE=copy
export PYTHONWARNINGS="ignore"
# ===========================
# Fully Automated Environment Setup Script
# ===========================

# 1. Set WSL hostname to wsl-ha-dev if not already set
=======

# 0. Set WSL hostname to wsl-ha-dev if not already set
>>>>>>> e31047b (chore: add clean_env.sh environment reset script)
if [ "$(hostname)" != "wsl-ha-dev" ]; then
  echo "Setting WSL hostname to wsl-ha-dev (requires sudo)..."
  echo "wsl-ha-dev" | sudo tee /etc/hostname
  sudo sed -i 's/127.0.1.1.*/127.0.1.1\twsl-ha-dev/' /etc/hosts
  sudo hostname wsl-ha-dev
<<<<<<< HEAD
  echo "Hostname changed. Please restart your WSL instance for changes to take effect."
fi

# 2. Reset upstream and clean untracked files
echo "1. Resetting to latest upstream/main..."
#git fetch upstream
#git reset --hard upstream/main

echo "2. Cleaning untracked files and directories..."
#git clean -fdx

# 3. Remove old virtual environment
echo "3. Removing old virtual environment..."
rm -rf .venv

# 4. Check and install Python 3.14+ with build tools
echo "4. Checking for Python 3.14+ support..."
if command -v python3.14 &> /dev/null; then
  PYTHON="python3.14"
  echo "Found python3.14."
elif command -v python3 &> /dev/null; then
  # Check if current python3 >= 3.14
  VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
  if [[ "$VERSION" =~ ^3\.1[4-9] || "$VERSION" =~ ^3\.[2-9][0-9] ]]; then
    PYTHON="python3"
    echo "Using existing python3, version: $VERSION"
  else
    echo "Python version is $VERSION, which is older than 3.14."
    echo "Attempting to install Python 3.14+ via deadsnakes PPA..."
    # Add deadsnakes PPA and install Python 3.14+ with build tools
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.14 python3.14-venv python3.14-dev build-essential
    # Ensure pip is installed
    python3.14 -m ensurepip --upgrade
    python3.14 -m pip install --upgrade pip
    PYTHON="python3.14"
    echo "Installed Python 3.14+."
  fi
else
  echo "Python 3 is not installed. Attempting to install Python 3.14+..."
  sudo apt update
  sudo apt install -y software-properties-common
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt update
  sudo apt install -y python3.14 python3.14-venv python3.14-dev build-essential
  python3.14 -m ensurepip --upgrade
  python3.14 -m pip install --upgrade pip
  PYTHON="python3.14"
  echo "Installed Python 3.14+."
fi

# 5. Create virtual environment
echo "5. Creating virtual environment..."
$PYTHON -m venv .venv
echo "Activate with: source .venv/bin/activate"

# 6. Activate virtual environment
source .venv/bin/activate

# 7. Upgrade pip and build tools
echo "6. Upgrading pip and build tools..."
pip install --upgrade pip build setuptools wheel

# 8. Install dependencies from pyproject.toml
echo "7. Installing dependencies from pyproject.toml..."
pip install --upgrade --use-pep517 .

# 9. Run tests
echo "8. Running test suite..."
uv run pytest tests

# 10. Final message
echo "Setup complete! You can now start working on your project."
=======
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

# 5. Installing dependencies...
if [ -f requirements.txt ]; then
  uv pip install -r requirements.txt
else
  uv pip install --from pyproject.toml
fi

echo "6. Running test suite..."
uv run pytest tests

echo "7. Checking Home Assistant integration loads (manual step):"
echo "   - Start Home Assistant and check logs for errors."
echo "   - Confirm at least one Renogy device is detected."

echo "8. Ready for new integration work!"

# Reminder: Run this script from outside your project, or re-copy it in after cleaning.
>>>>>>> e31047b (chore: add clean_env.sh environment reset script)
