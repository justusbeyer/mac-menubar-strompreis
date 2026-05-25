.PHONY: all build clean venv

VENV    := .venv
PYTHON  := $(VENV)/bin/python3
PIP     := $(VENV)/bin/pip

all: build

## Create virtual environment and install dependencies
venv: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install py2app
	@touch $(VENV)/bin/activate

## Build .app bundle
build: venv
	$(PYTHON) setup.py py2app

## Delete temporary build artifacts
clean:
	rm -rf build dist $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
