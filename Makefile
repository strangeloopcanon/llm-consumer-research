.PHONY: setup ensure-venv check test llm-live deps-audit all gradio

PYTHON_BIN ?= python3.11
VENV ?= .venv311
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest
BANDIT := $(VENV)/bin/bandit
PIP_AUDIT := $(VENV)/bin/pip-audit
PIP_AUDIT_FLAGS ?= --ignore-vuln GHSA-4xh5-x5gv-qwph

setup:
	@echo "==> Creating virtual environment in $(VENV)"
	$(PYTHON_BIN) -m venv $(VENV)
	@echo "==> Upgrading pip"
	$(PYTHON) -m pip install --upgrade pip
	@echo "==> Installing project dependencies"
	$(PIP) install -e .[dev]

ensure-venv:
	@test -x $(PYTHON) || (echo "Virtualenv not found. Run 'make setup' first." && exit 4)

check: ensure-venv
	$(RUFF) check .
	$(MYPY) src tests
	$(BANDIT) -q -r src

test: ensure-venv
	$(PYTEST) --maxfail=1 --disable-warnings

llm-live: ensure-venv
	$(PYTEST) -m llm_live tests_llm_live

deps-audit: ensure-venv
	$(PIP_AUDIT) $(PIP_AUDIT_FLAGS)

all: check test llm-live

gradio: ensure-venv
	@if [ ! -f .env ] && [ -z "$$OPENAI_API_KEY" ]; then \
		echo "OPENAI_API_KEY is not set and .env is missing. Add it to .env or export it before running 'make gradio'."; \
		exit 1; \
	fi
	@set -a; \
	[ -f .env ] && . ./.env; \
	set +a; \
	AGENT_MODE=$${AGENT_MODE:-baseline}; \
	if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "OPENAI_API_KEY is required to launch Gradio."; \
		exit 1; \
	fi; \
	echo "Launching Gradio with AGENT_MODE=$${AGENT_MODE}"; \
	AGENT_MODE=$$AGENT_MODE OPENAI_API_KEY=$$OPENAI_API_KEY $(PYTHON) gradio_app.py
