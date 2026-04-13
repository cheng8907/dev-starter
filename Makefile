CC := cc
CXX := c++
PYTHON := ./.venv/bin/python
VENV := .venv
BIN_DIR := build/bin
CMAKE_BUILD_DIR := build/cmake

.PHONY: all c cpp python run-c run-cpp run-python venv cmake cmake-build clean help

all: c cpp

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

c: $(BIN_DIR)
	$(CC) -Wall -Wextra -Wpedantic -std=c11 src/c/main.c -o $(BIN_DIR)/c_app

cpp: $(BIN_DIR)
	$(CXX) -Wall -Wextra -Wpedantic -std=c++17 src/cpp/main.cpp -o $(BIN_DIR)/cpp_app

python:
	$(PYTHON) python/main.py

run-c: c
	./$(BIN_DIR)/c_app

run-cpp: cpp
	./$(BIN_DIR)/cpp_app

run-python:
	$(PYTHON) python/main.py

venv:
	uv venv --python 3.13 $(VENV)
	./$(VENV)/bin/python -m ensurepip --upgrade
	./$(VENV)/bin/python -m pip install --upgrade pip
	./$(VENV)/bin/python -m pip install -r requirements.txt
	./$(VENV)/bin/python -m pip install -r requirements-dev.txt

cmake:
	cmake -S . -B $(CMAKE_BUILD_DIR) -G Ninja

cmake-build: cmake
	cmake --build $(CMAKE_BUILD_DIR)

clean:
	rm -rf build __pycache__

help:
	@echo "Targets:"
	@echo "  make c          Build the C sample"
	@echo "  make cpp        Build the C++ sample"
	@echo "  make run-c      Build and run the C sample"
	@echo "  make run-cpp    Build and run the C++ sample"
	@echo "  make run-python Run the Python sample"
	@echo "  make venv       Create the Python virtual environment"
	@echo "  make cmake      Configure a Ninja-based CMake build"
	@echo "  make cmake-build Configure and build via CMake"
	@echo "  make clean      Remove build output"
