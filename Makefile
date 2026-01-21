.PHONY: setup ensure-venv check test llm-live deps-audit all

PYTHON_BIN ?= python3.11
VENV ?= .venv311
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
RUFF := $(VENV)/bin/ruff
TY := $(VENV)/bin/ty
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
	$(TY) check src tests
	$(BANDIT) -q -r src

test: ensure-venv
	$(PYTEST) --maxfail=1 --disable-warnings

llm-live: ensure-venv
	$(PYTEST) -m llm_live tests_llm_live

deps-audit: ensure-venv
	$(PIP_AUDIT) $(PIP_AUDIT_FLAGS)

all: check test llm-live
