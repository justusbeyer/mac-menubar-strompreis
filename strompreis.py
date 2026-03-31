#!/usr/bin/env python3
"""
Strompreis Menubar App für macOS
Zeigt den aktuellen Börsenstrompreis für Deutschland (EPEX Spot) in der Menüleiste an.
Der Preis wird beim Start geladen und danach jeweils zur vollen Stunde aktualisiert,
wenn der angezeigte Preis seine Gültigkeit verliert.
Datenquelle: aWATTar API (kostenlos, keine Registrierung nötig)
"""

import rumps
import requests
import logging
import threading
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import time


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


API_URL = "https://api.awattar.de/v1/marketdata"

# Aufschläge und Steuern (beispielhaft, Stand 2024)
# Netzentgelt + Umlagen + Steuern ca. 20 ct/kWh zusätzlich zum Börsenpreis
# Der Börsenpreis wird in EUR/MWh geliefert → Umrechnung in ct/kWh: / 10
SURCHARGE_CT_PER_KWH = 20.0  # Aufschlag in Cent/kWh (Netz, Umlagen, Steuern)
VAT_FACTOR = 1.19             # Mehrwertsteuer 19 %


def get_current_market_price():
    """
    Ruft den aktuellen stündlichen Börsenpreis von der aWATTar-API ab.
    Gibt Nettopreis (ct/kWh), Bruttopreis (ct/kWh), Gültigkeitsende als
    Zeitstring sowie den End-Timestamp in Millisekunden zurück.
    """
    now_ms = int(time.time() * 1000)
    params = {
        "start": now_ms - 3600 * 1000,  # eine Stunde zurück
        "end":   now_ms + 3600 * 1000,  # eine Stunde voraus
    }
    resp = requests.get(API_URL, params=params, timeout=10)
    logger.info("GET %s – HTTP %s", API_URL, resp.status_code)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    if not data:
        return None, None, None, None

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
            return price_ct_kwh, price_gross, valid_until, entry["end_timestamp"]

    # Fallback: neuesten Eintrag nehmen
    entry = sorted(data, key=lambda x: x["start_timestamp"])[-1]
    price_eur_mwh = entry["marketprice"]
    price_ct_kwh = price_eur_mwh / 10.0
    price_gross = (price_ct_kwh + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
    valid_until = datetime.fromtimestamp(
        entry["end_timestamp"] / 1000
    ).strftime("%H:%M")
    return price_ct_kwh, price_gross, valid_until, entry["end_timestamp"]


RETRY_INTERVAL_S = 3 * 60  # Wartezeit nach einem fehlgeschlagenen API-Aufruf


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

        self._expiry_timer = None  # einmaliger Timer zum Preisablauf
        self._timer_lock = threading.Lock()  # schützt _expiry_timer vor Race Conditions

        # Beim Start sofort laden; danach übernimmt _schedule_expiry_refresh
        self.update_price(None)

    def _schedule_expiry_refresh(self, end_timestamp_ms):
        """Setzt einen einmaligen Timer, der genau beim Ablauf des aktuellen Preises feuert."""
        with self._timer_lock:
            if self._expiry_timer is not None:
                self._expiry_timer.cancel()
                self._expiry_timer = None

            seconds_until_expiry = (end_timestamp_ms / 1000) - time.time()
            if seconds_until_expiry <= 5:
                return  # Preis läuft sofort ab oder ist bereits abgelaufen – kein Timer nötig

            def _on_expiry():
                with self._timer_lock:
                    self._expiry_timer = None
                self.update_price(None)

            self._expiry_timer = threading.Timer(seconds_until_expiry, _on_expiry)
            self._expiry_timer.daemon = True
            self._expiry_timer.start()
            logger.info("Expiry-Timer gesetzt: Aktualisierung in %.0f s", seconds_until_expiry)

    def _schedule_retry(self):
        """Setzt einen einmaligen Timer für einen erneuten Abrufversuch nach RETRY_INTERVAL_S."""
        with self._timer_lock:
            if self._expiry_timer is not None:
                self._expiry_timer.cancel()
                self._expiry_timer = None
        t = threading.Timer(RETRY_INTERVAL_S, self.update_price, args=[None])
        t.daemon = True
        t.start()
        logger.info("Retry geplant in %d s", RETRY_INTERVAL_S)

    @rumps.clicked("Jetzt aktualisieren")
    def manual_refresh(self, _):
        self.update_price(None)

    def update_price(self, _):
        """Holt den aktuellen Preis und aktualisiert Titel und Menü."""
        try:
            raw, gross, valid_until, end_ts = get_current_market_price()

            if raw is None:
                self.title = "⚡ n/a"
                self.last_update_item.title = "Keine Daten verfügbar"
                self._schedule_retry()
                return

            # Titelleiste: reiner Börsenpreis
            raw_rounded = str(Decimal(str(raw)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)).replace(".", ",")
            self.title = f"⚡ {raw_rounded}ct/kWh"

            now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
            self.last_update_item.title = f"Aktualisiert: {now_str}"
            self.raw_price_item.title   = f"Börsenpreis: {raw:.2f} ct/kWh"
            self.gross_price_item.title = f"Bruttopreis (ca.): {gross:.2f} ct/kWh *"
            self.valid_until_item.title = f"Gültig bis: {valid_until} Uhr"

            # Timer für den Ablauf des aktuellen Preises setzen
            self._schedule_expiry_refresh(end_ts)

        except requests.exceptions.ConnectionError:
            logger.error("API-Aufruf fehlgeschlagen: Keine Verbindung")
            self.title = "⚡ offline"
            self.last_update_item.title = "Fehler: Keine Verbindung"
            self._schedule_retry()
        except requests.exceptions.Timeout:
            logger.error("API-Aufruf fehlgeschlagen: Zeitüberschreitung")
            self.title = "⚡ timeout"
            self.last_update_item.title = "Fehler: Zeitüberschreitung"
            self._schedule_retry()
        except Exception as e:
            logger.error("Unerwarteter Fehler: %s", e)
            self.title = "⚡ Fehler"
            self.last_update_item.title = f"Fehler: {str(e)[:50]}"
            self._schedule_retry()


if __name__ == "__main__":
    StrompreisApp().run()
