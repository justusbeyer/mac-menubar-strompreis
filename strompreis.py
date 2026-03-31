#!/usr/bin/env python3
"""
Strompreis Menubar App für macOS
Zeigt den aktuellen Börsenstrompreis für Deutschland (EPEX Spot) in der Menüleiste an.
Datenquelle: aWATTar API (kostenlos, keine Registrierung nötig)
"""

import rumps
import requests
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import time


API_URL = "https://api.awattar.de/v1/marketdata"

# Aufschläge und Steuern (beispielhaft, Stand 2024)
# Netzentgelt + Umlagen + Steuern ca. 20 ct/kWh zusätzlich zum Börsenpreis
# Der Börsenpreis wird in EUR/MWh geliefert → Umrechnung in ct/kWh: / 10
SURCHARGE_CT_PER_KWH = 20.0  # Aufschlag in Cent/kWh (Netz, Umlagen, Steuern)
VAT_FACTOR = 1.19             # Mehrwertsteuer 19 %


def get_current_market_price():
    """
    Ruft den aktuellen stündlichen Börsenpreis von der aWATTar-API ab.
    Gibt den Preis in ct/kWh zurück (Bruttopreis inkl. Aufschlägen).
    """
    now_ms = int(time.time() * 1000)
    params = {
        "start": now_ms - 3600 * 1000,  # eine Stunde zurück
        "end":   now_ms + 3600 * 1000,  # eine Stunde voraus
    }
    resp = requests.get(API_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    if not data:
        return None, None, None

    # Den Eintrag finden, in dessen Zeitfenster der aktuelle Zeitpunkt fällt
    for entry in data:
        if entry["start_timestamp"] <= now_ms < entry["end_timestamp"]:
            price_eur_mwh = entry["marketprice"]
            # EUR/MWh → ct/kWh: 1 MWh = 1000 kWh, 1 EUR = 100 ct
            # EUR/MWh * 100 ct/EUR / 1000 kWh/MWh = ct/kWh / 10
            price_ct_kwh = price_eur_mwh / 10.0
            # Bruttopreis mit Aufschlag und MwSt.
            price_gross = (price_ct_kwh + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
            valid_until = datetime.fromtimestamp(
                entry["end_timestamp"] / 1000
            ).strftime("%H:%M")
            return price_ct_kwh, price_gross, valid_until

    # Fallback: neuesten Eintrag nehmen
    entry = sorted(data, key=lambda x: x["start_timestamp"])[-1]
    price_eur_mwh = entry["marketprice"]
    price_ct_kwh = price_eur_mwh / 10.0
    price_gross = (price_ct_kwh + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
    valid_until = datetime.fromtimestamp(
        entry["end_timestamp"] / 1000
    ).strftime("%H:%M")
    return price_ct_kwh, price_gross, valid_until


def price_emoji(price_ct):
    """Gibt ein Emoji abhängig vom Preisniveau zurück."""
    if price_ct is None:
        return "?"
    if price_ct < 5:
        return "green_circle"   # sehr günstig
    elif price_ct < 15:
        return "yellow_circle"  # normal
    elif price_ct < 25:
        return "orange_circle"  # teuer
    else:
        return "red_circle"     # sehr teuer


class StrompreisApp(rumps.App):
    def __init__(self):
        super().__init__(
            name="Strompreis",
            title="⚡ ...",
            quit_button=None,
        )

        # Menüeinträge
        self.last_update_item = rumps.MenuItem("Letzte Aktualisierung: –")
        self.raw_price_item   = rumps.MenuItem("Börsenpreis: –")
        self.gross_price_item = rumps.MenuItem("Bruttopreis (ca.): –")
        self.valid_until_item = rumps.MenuItem("Gültig bis: –")
        self.note_item        = rumps.MenuItem(
            "* Aufschlag: Netz + Umlagen + MwSt."
        )
        self.refresh_item     = rumps.MenuItem(
            "Jetzt aktualisieren", callback=self.manual_refresh
        )
        self.quit_item        = rumps.MenuItem(
            "Beenden", callback=rumps.quit_application
        )

        self.menu = [
            self.last_update_item,
            None,  # Trennlinie
            self.raw_price_item,
            self.gross_price_item,
            self.valid_until_item,
            None,
            self.note_item,
            None,
            self.refresh_item,
            self.quit_item,
        ]

        # Sofort beim Start laden, dann alle 15 Minuten
        self.update_price(None)
        self.timer = rumps.Timer(self.update_price, 15 * 60)
        self.timer.start()

    @rumps.clicked("Jetzt aktualisieren")
    def manual_refresh(self, _):
        self.update_price(None)

    def update_price(self, _):
        """Holt den aktuellen Preis und aktualisiert Titel und Menü."""
        try:
            raw, gross, valid_until = get_current_market_price()

            if raw is None:
                self.title = "⚡ n/a"
                self.last_update_item.title = "Keine Daten verfügbar"
                return

            # Titelleiste: reiner Börsenpreis
            raw_rounded = str(Decimal(str(raw)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)).replace(".", ",")
            self.title = f"⚡ {raw_rounded}ct/kWh"

            now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
            self.last_update_item.title = f"Aktualisiert: {now_str}"
            self.raw_price_item.title   = f"Börsenpreis: {raw:.2f} ct/kWh"
            self.gross_price_item.title = f"Bruttopreis (ca.): {gross:.2f} ct/kWh *"
            self.valid_until_item.title = f"Gültig bis: {valid_until} Uhr"

        except requests.exceptions.ConnectionError:
            self.title = "⚡ offline"
            self.last_update_item.title = "Fehler: Keine Verbindung"
        except requests.exceptions.Timeout:
            self.title = "⚡ timeout"
            self.last_update_item.title = "Fehler: Zeitüberschreitung"
        except Exception as e:
            self.title = "⚡ Fehler"
            self.last_update_item.title = f"Fehler: {str(e)[:50]}"


if __name__ == "__main__":
    StrompreisApp().run()
