#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "Creating Python virtual environment..."
uv python install 3.13
uv venv --python 3.13 .venv

echo "Installing Python development dependencies..."
./.venv/bin/python -m ensurepip --upgrade
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install -r requirements-dev.txt

echo "Environment ready."
echo "C compiler: $(cc --version | head -n 1)"
echo "C++ compiler: $(c++ --version | head -n 1)"
echo "Python: $(./.venv/bin/python --version)"
echo
echo "Try:"
echo "  make run-c"
echo "  make run-cpp"
echo "  source .venv/bin/activate && python python/main.py"
