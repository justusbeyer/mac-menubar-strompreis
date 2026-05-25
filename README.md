# Strompreis Menubar App

A macOS menubar application that displays the current wholesale electricity price for Germany.
The price is loaded at startup and automatically refreshed each hour when the displayed price expires.

## Data Source

[aWATTar API](https://api.awattar.de/v1/marketdata) — free, no registration required.  
The wholesale price corresponds to the EPEX Spot Day-Ahead price in EUR/MWh.

## Price Calculation

| Component | Value |
|---|---|
| Wholesale price | variable (hourly) |
| Surcharge (grid, levies) | ~20 ct/kWh |
| VAT | 19% |

> The displayed **gross price** is an approximation. The actual price depends on your tariff and grid area.

## Installation

### Prerequisites

- macOS
- Python 3.9+
- make

### Build app bundle (recommended)

```bash
cd mac-menubar-strompreis
make
```

The bundle is created at `dist/Strompreis.app` and can be launched by double-clicking from there or moved to `/Applications/`.

### Makefile commands

| Command | Description |
|---|---|
| `make` / `make build` | Create virtual environment and build `dist/Strompreis.app` |
| `make venv` | Only create virtual environment and install dependencies |
| `make clean` | Delete `build/`, `dist/`, and `.venv/` |

### Run script directly (without bundle)

```bash
cd mac-menubar-strompreis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 strompreis.py
```

## Autostart at login (optional)

Set up a LaunchAgent to start the app automatically at login:

```bash
# Adjust paths!
cp de.strompreis.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/de.strompreis.plist
```

Before copying, adjust the paths in `de.strompreis.plist`:
- `/PATH/TO/.venv/bin/python3` → your Python interpreter
- `/PATH/TO/mac-menubar-strompreis/strompreis.py` → location of the app

## Menu

```
⚡ 8,1ct/kWh             ← Wholesale price in the menu bar
─────────────────────────
Aktualisiert: 31.03.2026 14:00
─────────────────────────
Börsenpreis: 10.53 ct/kWh
Bruttopreis (ca.): 32.47 ct/kWh *
Gültig bis: 15:00 Uhr
─────────────────────────
* Aufschlag: Netz + Umlagen + MwSt.
─────────────────────────
Jetzt aktualisieren
Beenden
```

## License

GPLv3
