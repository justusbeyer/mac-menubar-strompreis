"""
Isolated test of the API logic from strompreis.py.
Runs without macOS GUI (no rumps required).
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

    # Fallback: use the latest entry
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
    print(f"  Wholesale price:   {raw:.2f} ct/kWh")
    print(f"  Gross price:       {gross:.2f} ct/kWh")
    print(f"  Valid until:       {valid_until} Uhr")


def test_price_types():
    raw, gross, _ = get_current_market_price()
    assert isinstance(raw, float), f"raw should be float, got {type(raw)}"
    assert isinstance(gross, float), f"gross should be float, got {type(gross)}"
    print(f"  Types correct: raw={type(raw).__name__}, gross={type(gross).__name__}")


def test_price_plausibility():
    raw, gross, _ = get_current_market_price()
    assert raw is not None and gross is not None
    assert -50 < raw < 500, f"raw price out of plausible range: {raw}"
    assert 0 < gross < 600,  f"gross price out of plausible range: {gross}"
    print(f"  Plausibility check passed: raw={raw:.2f}, gross={gross:.2f}")


def test_gross_greater_than_raw():
    raw, gross, _ = get_current_market_price()
    assert raw is not None and gross is not None
    # gross = (raw + 20) * 1.19 — should always be > raw (for positive raw)
    if raw >= 0:
        assert gross > raw, f"gross ({gross:.2f}) should be > raw ({raw:.2f})"
    print(f"  Gross price ({gross:.2f}) > Wholesale price ({raw:.2f}): OK")


def test_valid_until_format():
    _, _, valid_until = get_current_market_price()
    assert valid_until is not None
    parts = valid_until.split(":")
    assert len(parts) == 2, f"Unexpected format: {valid_until}"
    h, m = int(parts[0]), int(parts[1])
    assert 0 <= h <= 23 and 0 <= m <= 59, f"Invalid time: {valid_until}"
    print(f"  Time format correct: {valid_until}")


def test_price_formula():
    """Formel: gross = (raw + SURCHARGE) * VAT"""
    raw, gross, _ = get_current_market_price()
    assert raw is not None and gross is not None
    expected = (raw + SURCHARGE_CT_PER_KWH) * VAT_FACTOR
    assert abs(gross - expected) < 0.001, f"Formula incorrect: {gross} != {expected}"
    print(f"  Formula correct: ({raw:.2f} + {SURCHARGE_CT_PER_KWH}) × {VAT_FACTOR} = {gross:.2f}")


if __name__ == "__main__":
    tests = [
        ("API returns data",              test_api_returns_data),
        ("Correct types",                 test_price_types),
        ("Price plausibility",            test_price_plausibility),
        ("Gross price > wholesale price", test_gross_greater_than_raw),
        ("Time format HH:MM",             test_valid_until_format),
        ("Price formula correct",         test_price_formula),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            print(f"  -> PASSED")
            passed += 1
        except Exception as e:
            print(f"  -> FAILED: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Result: {passed}/{len(tests)} tests passed", end="")
    print(f" | {failed} failed" if failed else "")
    print('='*50)
    exit(0 if failed == 0 else 1)
