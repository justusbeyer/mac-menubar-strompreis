.PHONY: all build clean venv

VENV    := .venv
PYTHON  := $(VENV)/bin/python3
PIP     := $(VENV)/bin/pip

all: build

## Virtuelle Umgebung erstellen und Abhängigkeiten installieren
venv: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install py2app
	@touch $(VENV)/bin/activate

## .app-Bundle bauen
build: venv
	$(PYTHON) setup.py py2app

## Temporäre Build-Artefakte löschen
clean:
	rm -rf build dist $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
