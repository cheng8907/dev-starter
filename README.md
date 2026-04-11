# Dev Starter

A fresh starter project for C, C++, and Python development on macOS.

GitHub repository: `https://github.com/cheng8907/dev-starter`

## Included

- `src/c/main.c`: C sample program
- `src/cpp/main.cpp`: C++ sample program
- `python/main.py`: Python sample program
- `Makefile`: build and run commands
- `CMakeLists.txt`: CMake build for the C and C++ programs
- `.vscode/`: editor tasks and recommendations
- `scripts/bootstrap.sh`: one-shot environment setup
- `LICENSE`: MIT license for the project

## Clone

```bash
git clone https://github.com/cheng8907/dev-starter.git
cd dev-starter
```

## Quick Start

```bash
cd /Users/cheng/Documents/dev-starter
./scripts/bootstrap.sh
make run-c
make run-cpp
source .venv/bin/activate
python python/main.py
```

## Build and Run

```bash
make c
make cpp
make run-c
make run-cpp
make run-python
```

## CMake Workflow

```bash
make cmake-build
./build/cmake/c_app
./build/cmake/cpp_app
```

## Python Environment

Create the virtual environment manually if you prefer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## OpenAI API Key

Store your key in `.env`:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

Keep the real key in `.env` and use [`.env.example`](/Users/cheng/Documents/dev-starter/.env.example) as the shareable template.

## Git Sync

The local `main` branch tracks `origin/main`, so normal GitHub sync commands work:

```bash
git pull
git push
```

## Optional Tooling

`cmake` and `ninja` are already installed on this machine.
