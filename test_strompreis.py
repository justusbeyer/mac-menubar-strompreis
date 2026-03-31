"""
Isolierter Test der API-Logik aus strompreis.py
Läuft ohne macOS-GUI (kein rumps nötig).
"""

import requests
import time
from datetime import datetime

API_URL = "https://api.awattar.de/v1/marketdata"
SURCHARGE_CT_PER_KWH = 20.0
VAT_FACTOR = 1.19


def get_current_market_price():
    now_ms = int(time.time() * 1000)
    params = {
        "start": now_ms - 3600 * 1000,
        "end":   now_ms + 3600 * 1000,
    }
    resp = requests.get(API_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    if not data:
        return None, None, None

    for entry in data:
        if entry["start_timestamp"] <= now_ms < entry["end_timestamp"]:
            price_eur_mwh = entry["marketprice"]
            price_ct_kwh  = price_eur_mwh / 10.0
            price_gross   = (price_ct_kwh + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
            valid_until   = datetime.fromtimestamp(
                entry["end_timestamp"] / 1000
            ).strftime("%H:%M")
            return price_ct_kwh, price_gross, valid_until

    # Fallback
    entry = sorted(data, key=lambda x: x["start_timestamp"])[-1]
    price_eur_mwh = entry["marketprice"]
    price_ct_kwh  = price_eur_mwh / 10.0
    price_gross   = (price_ct_kwh + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
    valid_until   = datetime.fromtimestamp(
        entry["end_timestamp"] / 1000
    ).strftime("%H:%M")
    return price_ct_kwh, price_gross, valid_until


# ── Tests ────────────────────────────────────────────────────────────────────

def test_api_returns_data():
    raw, gross, valid_until = get_current_market_price()
    assert raw is not None, "raw price is None"
    assert gross is not None, "gross price is None"
    assert valid_until is not None, "valid_until is None"
    print(f"  Börsenpreis:   {raw:.2f} ct/kWh")
    print(f"  Bruttopreis:   {gross:.2f} ct/kWh")
    print(f"  Gültig bis:    {valid_until} Uhr")


def test_price_types():
    raw, gross, _ = get_current_market_price()
    assert isinstance(raw, float), f"raw should be float, got {type(raw)}"
    assert isinstance(gross, float), f"gross should be float, got {type(gross)}"
    print(f"  Typen korrekt: raw={type(raw).__name__}, gross={type(gross).__name__}")


def test_price_plausibility():
    raw, gross, _ = get_current_market_price()
    assert raw is not None and gross is not None
    assert -50 < raw < 500, f"raw price out of plausible range: {raw}"
    assert 0 < gross < 600,  f"gross price out of plausible range: {gross}"
    print(f"  Plausibilitätsprüfung bestanden: raw={raw:.2f}, gross={gross:.2f}")


def test_gross_greater_than_raw():
    raw, gross, _ = get_current_market_price()
    assert raw is not None and gross is not None
    # gross = (raw + 20) * 1.19 — sollte immer > raw sein (bei positivem raw)
    if raw >= 0:
        assert gross > raw, f"gross ({gross:.2f}) sollte > raw ({raw:.2f}) sein"
    print(f"  Bruttopreis ({gross:.2f}) > Börsenpreis ({raw:.2f}): OK")


def test_valid_until_format():
    _, _, valid_until = get_current_market_price()
    assert valid_until is not None
    parts = valid_until.split(":")
    assert len(parts) == 2, f"Unerwartetes Format: {valid_until}"
    h, m = int(parts[0]), int(parts[1])
    assert 0 <= h <= 23 and 0 <= m <= 59, f"Ungültige Uhrzeit: {valid_until}"
    print(f"  Zeitformat korrekt: {valid_until}")


def test_price_formula():
    """Formel: gross = (raw + SURCHARGE) * VAT"""
    raw, gross, _ = get_current_market_price()
    assert raw is not None and gross is not None
    expected = (raw + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
    assert abs(gross - expected) < 0.001, f"Formel falsch: {gross} != {expected}"
    print(f"  Formel korrekt: ({raw:.2f} + {SURCHARGE_CT_PER_KWH}) × {VAT_FACTOR} = {gross:.2f}")


if __name__ == "__main__":
    tests = [
        ("API liefert Daten",           test_api_returns_data),
        ("Datentypen korrekt",          test_price_types),
        ("Preisplausibilität",          test_price_plausibility),
        ("Bruttopreis > Börsenpreis",   test_gross_greater_than_raw),
        ("Zeitformat HH:MM",            test_valid_until_format),
        ("Preisformel korrekt",         test_price_formula),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            print(f"  -> BESTANDEN")
            passed += 1
        except Exception as e:
            print(f"  -> FEHLGESCHLAGEN: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Ergebnis: {passed}/{len(tests)} Tests bestanden", end="")
    print(f" | {failed} fehlgeschlagen" if failed else "")
    print('='*50)
    exit(0 if failed == 0 else 1)
