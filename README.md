# Dev Starter

A starter workspace for Polymarket API development with Python on macOS, plus the original C and C++ samples.

GitHub repository: `https://github.com/cheng8907/dev-starter`

## Included

- `python/main.py`: Polymarket API connectivity check using direct HTTP calls
- `requirements.txt`: Python runtime dependencies for Polymarket development
- `.env.example`: shareable Polymarket environment variable template
- `scripts/bootstrap.sh`: one-shot local environment setup
- `Makefile`: build and run commands
- `src/c/main.c`: C sample program
- `src/cpp/main.cpp`: C++ sample program

## Clone

```bash
git clone https://github.com/cheng8907/dev-starter.git
cd dev-starter
```

## Quick Start

```bash
./scripts/bootstrap.sh
cp .env.example .env
source .venv/bin/activate
python python/main.py
```

The default script runs in read-only mode against Polymarket's CLOB API. If you later want authenticated trading actions, the environment file is already prepared for wallet-related variables.

## Environment Variables

Copy [`.env.example`](/Users/chengchen/Documents/dev-starter/.env.example) to `.env` and fill in what you need:

```env
POLYMARKET_HOST=https://clob.polymarket.com
POLYMARKET_CHAIN_ID=137
POLYMARKET_PRIVATE_KEY=
POLYMARKET_FUNDER=
```

Notes:

- `POLYMARKET_HOST` defaults to the official CLOB endpoint.
- `POLYMARKET_CHAIN_ID=137` is Polygon mainnet.
- Leave `POLYMARKET_PRIVATE_KEY` and `POLYMARKET_FUNDER` blank for read-only API calls.
- Add wallet values later if you decide to move from market-data or health-check calls into authenticated trading flows.

## Python Environment

Create the virtual environment manually if you prefer:

```bash
uv python install 3.13
uv venv --python 3.13 .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

This project targets Python `3.13` for Polymarket work because the dependency stack is more dependable there than on Python `3.14`.

## Run

```bash
source .venv/bin/activate
python python/main.py
make run-python
```

The script prints:

- whether the Polymarket API is healthy
- the current server time
- whether the project is running in read-only or authenticated-ready mode

## Calendar Core Module

The project also now includes a reusable calendar backend module in [`python/calendar_core`](/Users/cheng/Documents/dev-starter/python/calendar_core).

This base module currently provides:

- timezone-aware event models
- in-memory repository storage
- event creation, update, deletion, and lookup
- range queries for events
- conflict detection for overlapping events

It is intentionally UI-free so it can be integrated later with APIs, automation workflows, agent tools, or desktop/mobile frontends without rewriting the calendar logic.

## Calendar Sync Integrations

There is now also a sync layer in [`python/calendar_sync`](/Users/cheng/Documents/dev-starter/python/calendar_sync) for integrating the local calendar module with external providers.

Supported providers in this base integration layer:

- Google Calendar
- Outlook Calendar through Microsoft Graph

The sync module is designed around reusable provider adapters and a shared sync service so it can later connect to other internal product modules as well.

Authentication is currently bearer-token based, which keeps the backend portable and UI-free. OAuth login screens and token refresh flows can be added later on top of the same sync interfaces.

## Finance Ledger Module

The project now includes a finance backend module in [`python/finance_core`](/Users/cheng/Documents/dev-starter/python/finance_core).

This ledger layer currently provides:

- account management
- transaction categories
- transaction creation, update, listing, and deletion
- calendar-linked expense creation
- simple category summaries
- simple account balance summaries

This is intended to be the money system of record for the app, while the calendar remains the time-based planning and logging layer.

## Build and Run Native Samples

```bash
make c
make cpp
make run-c
make run-cpp
```

## CMake Workflow

```bash
make cmake-build
./build/cmake/c_app
./build/cmake/cpp_app
```

## Git Sync

The local `main` branch tracks `origin/main`, so normal GitHub sync commands work:

```bash
git pull
git push
```
