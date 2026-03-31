# Strompreis Menubar App

Eine macOS Menubar-Applikation, die den aktuellen Börsenstrompreis für Deutschland anzeigt.
Der Preis wird beim Start geladen und danach automatisch zur vollen Stunde aktualisiert, sobald der angezeigte Preis seine Gültigkeit verliert.

## Datenquelle

[aWATTar API](https://api.awattar.de/v1/marketdata) — kostenlos, keine Registrierung erforderlich.  
Der Börsenpreis entspricht dem EPEX Spot Day-Ahead-Preis in EUR/MWh.

## Preisberechnung

| Komponente | Wert |
|---|---|
| Börsenpreis | variabel (stündlich) |
| Aufschlag (Netz, Umlagen) | ~20 ct/kWh |
| MwSt. | 19 % |

> Der angezeigte **Bruttopreis** ist ein Näherungswert. Der tatsächliche Preis hängt von deinem Tarif und Netzgebiet ab.

## Installation

### Voraussetzungen

- macOS
- Python 3.9+
- make

### App-Bundle bauen (empfohlen)

```bash
cd mac-menubar-strompreis
make
```

Das Bundle wird unter `dist/Strompreis.app` abgelegt und kann von dort per Doppelklick gestartet oder nach `/Applications/` verschoben werden.

### Makefile-Befehle

| Befehl | Beschreibung |
|---|---|
| `make` / `make build` | Virtuelle Umgebung einrichten und `dist/Strompreis.app` bauen |
| `make venv` | Nur virtuelle Umgebung und Abhängigkeiten installieren |
| `make clean` | `build/`, `dist/` und `.venv/` löschen |

### Skript direkt starten (ohne Bundle)

```bash
cd mac-menubar-strompreis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 strompreis.py
```

## Autostart beim Login (optional)

Einen LaunchAgent einrichten, damit die App beim Login automatisch startet:

```bash
# Pfade anpassen!
cp de.strompreis.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/de.strompreis.plist
```

Vor dem Kopieren die Pfade in `de.strompreis.plist` anpassen:
- `/PFAD/ZU/.venv/bin/python3` → dein Python-Interpreter
- `/PFAD/ZU/mac-menubar-strompreis/strompreis.py` → Speicherort der App

## Menü

```
⚡ 8,1ct/kWh             ← Börsenpreis in der Menüleiste
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

## Lizenz

GPLv3
