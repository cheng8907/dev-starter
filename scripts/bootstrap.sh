#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "Creating Python virtual environment..."
python3 -m venv .venv

echo "Installing Python development dependencies..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements-dev.txt

echo "Environment ready."
echo "C compiler: $(cc --version | head -n 1)"
echo "C++ compiler: $(c++ --version | head -n 1)"
echo "Python: $(./.venv/bin/python --version)"
echo
echo "Try:"
echo "  make run-c"
echo "  make run-cpp"
echo "  source .venv/bin/activate && python python/main.py"

