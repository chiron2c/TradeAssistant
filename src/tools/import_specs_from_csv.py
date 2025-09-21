import csv, json, math, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root (…/TradeAssistant)
BROKERS = ROOT / "brokers"

DEFAULTS = {
    "indices": {
        "digits": 2,
        "tick_size": 0.01,
        "contract_size": 1.0,
        "min_lot": 0.01,
        "lot_step": 0.01,
        "max_lot": 100.0,
        "typical_points": 0,
        "swaps_type": "in points",  # some brokers use "in percentage terms"
        "triple_day": "Wednesday",
        "quote_ccy": "USD",
    }
    # add other categories here if needed
}

def fnum(x):
    # returns float if possible, else string unchanged (for empty cells)
    try:
        if x is None: return None
        s = str(x).strip()
        if s == "": return None
        return float(s)
    except Exception:
        return x

def build_json(row):
    broker   = row["broker"].strip()
    cat      = row["category"].strip()
    mkt      = row["market_code"].strip()
    symbol   = row["symbol"].strip()

    d = DEFAULTS.get(cat, DEFAULTS["indices"])

    digits    = int(row.get("digits") or d["digits"])
    tick_size = fnum(row.get("tick_size")) or d["tick_size"]
    csize     = fnum(row.get("contract_size")) or d["contract_size"]
    tv1lot    = fnum(row.get("tick_value_per_1lot"))  # required (validator wants this key)

    if tv1lot is None:
        # fallback heuristic: assume per 1.0 point value equals contract_size USD
        # so per-tick value = (contract_size * tick_size)
        tv1lot = round(csize * tick_size, 2)

    # derive per-point value hint for clarity
    per_point = round(tv1lot / tick_size, 2) if tick_size else None
    pv_hint = f"1.0 index point = USD {per_point:.2f} per lot" if per_point is not None else None

    min_lot = fnum(row.get("min_lot")) or d["min_lot"]
    lot_step = fnum(row.get("lot_step")) or d["lot_step"]
    max_lot = fnum(row.get("max_lot")) or d["max_lot"]
    typical_points = int(fnum(row.get("typical_points")) or d["typical_points"])

    swaps_type = (row.get("swaps_type") or d["swaps_type"]).strip()
    s_long  = fnum(row.get("swap_long"))
    s_short = fnum(row.get("swap_short"))
    triple  = (row.get("triple_day") or d["triple_day"]).strip()

    thours  = row.get("trading_hours_raw","").strip()
    qccy    = (row.get("quote_ccy") or d["quote_ccy"]).strip()
    notes   = row.get("notes","").strip()

    data = {
        "market_code": mkt,
        "broker": broker,
        "symbol": symbol,
        "price": {
            "digits": digits,
            "tick_size": tick_size,
            "tick_value_per_1lot": tv1lot,
            "contract_size": csize,
        },
        "volume": {
            "min_lot": min_lot,
            "lot_step": lot_step,
            "max_lot": max_lot,
        },
        "spread": {
            "type": "floating",
            "typical_points": typical_points,
        },
        "swaps": {
            "type": swaps_type,
            "long": s_long if s_long is not None else "TBD",
            "short": s_short if s_short is not None else "TBD",
            "triple_day": triple,
        },
        "trading_hours_raw": thours,
        "quote_ccy": qccy,
        "notes": notes or "From CSV importer.",
    }

    if pv_hint:
        data["price"]["point_value_hint"] = pv_hint

    return data, broker, cat, mkt

def save_json(data, broker, cat, mkt):
    out_dir = BROKERS / broker / "specs" / cat
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{mkt}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"OK: wrote {out_path.relative_to(ROOT)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/tools/import_specs_from_csv.py imports/markets.csv")
        sys.exit(2)

    csv_path = Path(sys.argv[1]).resolve()
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data, broker, cat, mkt = build_json(row)
            save_json(data, broker, cat, mkt)

if __name__ == "__main__":
    main()
