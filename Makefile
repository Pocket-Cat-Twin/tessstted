# Makefile for Game Monitor System
# Professional development and deployment automation

# Variables
PYTHON := python3
PIP := pip
VENV := venv
SRC := game_monitor
TESTS := tests
DOCS := docs

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help install install-dev test test-coverage clean build deploy docker-build docker-run setup lint format typecheck benchmark profile docs

# Default target
help: ## Show this help message
	@echo "$(BLUE)Game Monitor System - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Setup and Installation
setup: ## Set up development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	./$(VENV)/bin/pip install --upgrade pip
	./$(VENV)/bin/pip install -r requirements.txt
	./$(VENV)/bin/pip install -e ".[dev]"
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV)/bin/activate$(NC)"

install: ## Install package in current environment
	@echo "$(BLUE)Installing Game Monitor...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	@echo "$(GREEN)Installation complete!$(NC)"

install-dev: ## Install with development dependencies
	@echo "$(BLUE)Installing Game Monitor with development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)Development installation complete!$(NC)"

# Database and System Setup
init-db: ## Initialize database
	@echo "$(BLUE)Initializing database...$(NC)"
	$(PYTHON) setup_database.py
	@echo "$(GREEN)Database initialized!$(NC)"

reset-db: ## Reset database (WARNING: destroys all data)
	@echo "$(YELLOW)WARNING: This will destroy all existing data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f data/game_monitor.db; \
		$(PYTHON) setup_database.py; \
		echo "$(GREEN)Database reset complete!$(NC)"; \
	else \
		echo "$(BLUE)Database reset cancelled.$(NC)"; \
	fi

# Testing
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTHON) -m pytest $(TESTS)/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest $(TESTS)/ --cov=$(SRC) --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

test-performance: ## Run performance benchmarks
	@echo "$(BLUE)Running performance benchmarks...$(NC)"
	$(PYTHON) test_system.py --benchmark
	$(PYTHON) -m pytest --benchmark-only $(TESTS)/

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTHON) test_system.py --integration

# Code Quality
lint: ## Run code linting
	@echo "$(BLUE)Running linting...$(NC)"
	flake8 $(SRC)/ $(TESTS)/
	@echo "$(GREEN)Linting complete!$(NC)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	black $(SRC)/ $(TESTS)/ *.py
	isort $(SRC)/ $(TESTS)/ *.py
	@echo "$(GREEN)Code formatted!$(NC)"

typecheck: ## Run type checking with mypy
	@echo "$(BLUE)Running type checking...$(NC)"
	mypy $(SRC)/ --ignore-missing-imports
	@echo "$(GREEN)Type checking complete!$(NC)"

check-all: lint typecheck test ## Run all code quality checks

# System Testing and Validation
system-test: ## Run complete system test
	@echo "$(BLUE)Running complete system test...$(NC)"
	$(PYTHON) test_system.py --comprehensive

validate: init-db system-test ## Validate complete system setup
	@echo "$(GREEN)System validation complete!$(NC)"

benchmark: ## Run system benchmarks
	@echo "$(BLUE)Running system benchmarks...$(NC)"
	$(PYTHON) test_system.py --performance --detailed
	@echo "$(GREEN)Benchmarks complete!$(NC)"

profile: ## Profile application performance
	@echo "$(BLUE)Profiling application...$(NC)"
	$(PYTHON) -m cProfile -o profile_output.prof $(SRC)/main.py
	$(PYTHON) -c "import pstats; pstats.Stats('profile_output.prof').sort_stats('tottime').print_stats(20)"
	@echo "$(GREEN)Profiling complete! Output in profile_output.prof$(NC)"

# Development Tools
gui: ## Launch GUI interface
	@echo "$(BLUE)Starting GUI interface...$(NC)"
	$(PYTHON) -m $(SRC).gui_interface

cli: ## Launch command-line interface
	@echo "$(BLUE)Starting CLI interface...$(NC)"
	$(PYTHON) main.py

demo: ## Run system demonstration
	@echo "$(BLUE)Starting system demonstration...$(NC)"
	$(PYTHON) test_system.py --demo

# Build and Distribution
clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .coverage htmlcov/
	rm -rf __pycache__/ */__pycache__/ */*/__pycache__/
	rm -f *.pyc */*.pyc */*/*.pyc
	rm -f profile_output.prof
	@echo "$(GREEN)Cleanup complete!$(NC)"

build: clean ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(NC)"
	$(PYTHON) setup.py sdist bdist_wheel
	@echo "$(GREEN)Build complete! Packages in dist/$(NC)"

build-executable: ## Build standalone executable
	@echo "$(BLUE)Building standalone executable...$(NC)"
	$(PIP) install pyinstaller
	pyinstaller --onefile --windowed --name="GameMonitor" main.py
	@echo "$(GREEN)Executable created in dist/$(NC)"

install-local: build ## Install from local build
	@echo "$(BLUE)Installing from local build...$(NC)"
	$(PIP) install dist/*.whl --force-reinstall
	@echo "$(GREEN)Local installation complete!$(NC)"

# Docker Support
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t game-monitor:latest .
	@echo "$(GREEN)Docker image built!$(NC)"

docker-run: ## Run Docker container
	@echo "$(BLUE)Starting Docker container...$(NC)"
	docker run -p 8080:8080 -v $(PWD)/data:/app/data game-monitor:latest

docker-dev: ## Run Docker container in development mode
	@echo "$(BLUE)Starting Docker container in development mode...$(NC)"
	docker run -it -v $(PWD):/app -p 8080:8080 game-monitor:latest /bin/bash

# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@mkdir -p $(DOCS)
	$(PYTHON) -c "import $(SRC); help($(SRC))" > $(DOCS)/api.txt
	@echo "$(GREEN)Documentation generated in $(DOCS)/$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	@echo "Documentation will be available at http://localhost:8000"
	cd $(DOCS) && $(PYTHON) -m http.server 8000

# Maintenance and Monitoring
logs: ## View recent logs
	@echo "$(BLUE)Recent system logs:$(NC)"
	@tail -f logs/game_monitor.log 2>/dev/null || echo "No logs found. Run 'make init-db' first."

logs-performance: ## View performance logs
	@echo "$(BLUE)Recent performance logs:$(NC)"
	@tail -f logs/performance.log 2>/dev/null || echo "No performance logs found."

logs-errors: ## View error logs
	@echo "$(BLUE)Recent error logs:$(NC)"
	@tail -f logs/errors.log 2>/dev/null || echo "No error logs found."

monitor: ## Monitor system performance
	@echo "$(BLUE)Monitoring system performance (Ctrl+C to stop)...$(NC)"
	@while true; do \
		$(PYTHON) -c "import psutil; print(f'CPU: {psutil.cpu_percent():.1f}%, Memory: {psutil.virtual_memory().percent:.1f}%')"; \
		sleep 2; \
	done

health-check: ## Perform system health check
	@echo "$(BLUE)Performing system health check...$(NC)"
	@$(PYTHON) -c "
import sys
import subprocess
import importlib
import sqlite3
import os

print('System Health Check')
print('=' * 50)

# Python version
print(f'Python Version: {sys.version.split()[0]}')

# Required packages
packages = ['pyautogui', 'cv2', 'pytesseract', 'PIL', 'numpy', 'keyboard', 'yaml', 'psutil']
for pkg in packages:
    try:
        importlib.import_module(pkg)
        print(f'✓ {pkg} - Available')
    except ImportError:
        print(f'✗ {pkg} - Missing')

# Tesseract OCR
try:
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        version = result.stdout.split()[1]
        print(f'✓ Tesseract OCR - Version {version}')
    else:
        print('✗ Tesseract OCR - Not working')
except:
    print('✗ Tesseract OCR - Not found')

# Database
try:
    if os.path.exists('data/game_monitor.db'):
        conn = sqlite3.connect('data/game_monitor.db')
        cursor = conn.execute('SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\"')
        table_count = cursor.fetchone()[0]
        conn.close()
        print(f'✓ Database - {table_count} tables found')
    else:
        print('⚠ Database - Not initialized (run make init-db)')
except Exception as e:
    print(f'✗ Database - Error: {e}')

# Directories
dirs = ['logs', 'data', 'config', 'validation']
for dir_name in dirs:
    if os.path.exists(dir_name):
        print(f'✓ Directory {dir_name} - Exists')
    else:
        print(f'✗ Directory {dir_name} - Missing')

print('=' * 50)
print('Health check complete!')
"

# Development Workflow
dev-setup: setup init-db ## Complete development setup
	@echo "$(GREEN)Development environment is ready!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. source $(VENV)/bin/activate"
	@echo "  2. make test"
	@echo "  3. make gui"

dev-reset: clean reset-db setup ## Reset development environment
	@echo "$(GREEN)Development environment reset complete!$(NC)"

quick-test: ## Quick test run (essential tests only)
	@echo "$(BLUE)Running quick tests...$(NC)"
	$(PYTHON) -m pytest $(TESTS)/ -k "not slow" -q

pre-commit: format lint typecheck test ## Run pre-commit checks
	@echo "$(GREEN)All pre-commit checks passed!$(NC)"

# Release Management
version: ## Show current version
	@$(PYTHON) -c "from $(SRC) import __version__; print('Current version:', __version__)"

release-check: clean build test-coverage typecheck ## Check release readiness
	@echo "$(GREEN)Release check complete!$(NC)"

# Help for common tasks
status: ## Show system status
	@echo "$(BLUE)Game Monitor System Status$(NC)"
	@echo "=========================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Working Directory: $$(pwd)"
	@echo "Virtual Environment: $$(if [ -d "$(VENV)" ]; then echo "Present"; else echo "Not found"; fi)"
	@echo "Database: $$(if [ -f "data/game_monitor.db" ]; then echo "Initialized"; else echo "Not initialized"; fi)"
	@echo "Config: $$(if [ -f "config/config.yaml" ]; then echo "Present"; else echo "Not found"; fi)"
	@echo ""
	@echo "$(YELLOW)Common commands:$(NC)"
	@echo "  make setup     - Set up development environment"
	@echo "  make test      - Run tests"
	@echo "  make gui       - Start GUI"
	@echo "  make help      - Show all commands"

# Advanced Features
install-hooks: ## Install git hooks
	@echo "$(BLUE)Installing git hooks...$(NC)"
	@if [ -d ".git" ]; then \
		echo "#!/bin/bash" > .git/hooks/pre-commit; \
		echo "make pre-commit" >> .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "$(GREEN)Git hooks installed!$(NC)"; \
	else \
		echo "$(YELLOW)Not a git repository. Skipping hook installation.$(NC)"; \
	fi

dependency-check: ## Check for outdated dependencies
	@echo "$(BLUE)Checking for outdated dependencies...$(NC)"
	$(PIP) list --outdated

update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements.txt

security-scan: ## Run security scan on dependencies
	@echo "$(BLUE)Running security scan...$(NC)"
	$(PIP) install safety
	safety check

# Performance and Debugging
debug: ## Run in debug mode
	@echo "$(BLUE)Starting in debug mode...$(NC)"
	GAME_MONITOR_DEBUG=1 $(PYTHON) main.py --debug --verbose

memory-profile: ## Profile memory usage
	@echo "$(BLUE)Profiling memory usage...$(NC)"
	$(PIP) install memory-profiler
	$(PYTHON) -m memory_profiler main.py

line-profile: ## Profile line-by-line performance
	@echo "$(BLUE)Running line-by-line profiler...$(NC)"
	$(PIP) install line_profiler
	kernprof -l -v main.py

# This help message is shown by default
.DEFAULT_GOAL := help