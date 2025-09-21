# --- src/tools/apply_index_specs.py ---
# Apply index pip_size, pip_value_quote_per_std_lot, min_lot, lot_step from
# config/index_specs.json to both output/specs_enriched.csv and output/plan_preview.csv.
# Computes pip_value_account_per_std_lot using per-broker USD->Account factor
# from config/account.json (fallback to default_fx_usd_to_account).

from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "output"
SPEC = OUT / "specs_enriched.csv"
PLAN = OUT / "plan_preview.csv"
CONF = ROOT / "config" / "account.json"
IDX  = ROOT / "config" / "index_specs.json"

def load_json(path: Path) -> dict:
    if not path.exists(): return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))  # tolerate BOM
    except Exception:
        return {}

def load_csv(p: Path) -> Tuple[List[Dict[str,str]], List[str]]:
    if not p.exists(): return [], []
    with p.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r); fields = r.fieldnames or []
    return rows, fields

def write_csv(p: Path, rows: List[Dict[str,str]], fields: List[str]) -> None:
    if not rows: return
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    print(f"[DONE] Wrote {len(rows)} rows -> {p}")

def ensure_fields(fields: List[str], needed: List[str]) -> List[str]:
    out = list(fields)
    for n in needed:
        if n not in out: out.append(n)
    return out

def is_index(row: Dict[str,str]) -> bool:
    return (row.get("asset_class") or "").lower() == "index"

def symbol_of(row: Dict[str,str]) -> str:
    return (row.get("symbol_norm") or row.get("symbol") or "").upper()

def broker_of(row: Dict[str,str]) -> str:
    return (row.get("broker") or "").lower()

def fx_for_broker(cfg: dict, broker: str) -> float:
    bsec = (cfg.get("brokers") or {}).get(broker, {})
    if "fx_usd_to_account" in bsec:
        return float(bsec["fx_usd_to_account"])
    return float(cfg.get("default_fx_usd_to_account", 1.0))

def apply_to_rows(rows: List[Dict[str,str]], fields: List[str], specs: dict, cfg: dict) -> int:
    changed = 0
    for r in rows:
        if not is_index(r): 
            continue
        sym = symbol_of(r)
        brk = broker_of(r)
        if not brk or brk not in specs: 
            continue
        conf = specs[brk].get(sym)
        if not conf:
            continue

        usd_fx = fx_for_broker(cfg, brk)

        # pip_size
        if conf.get("pip_size") is not None:
            r["pip_size"] = f"{float(conf['pip_size']):.2f}"

        # pip value (quote) and derived account value
        if conf.get("pip_value_quote_per_std_lot") is not None:
            q = float(conf["pip_value_quote_per_std_lot"])
            r["pip_value_quote_per_std_lot"]   = f"{q:.6f}"
            r["pip_value_account_per_std_lot"] = f"{q * usd_fx:.6f}"

        # min lot / step
        if conf.get("min_lot") is not None:
            r["min_lot"] = f"{float(conf['min_lot']):.2f}"
        if conf.get("lot_step") is not None:
            r["lot_step"] = f"{float(conf['lot_step']):.2f}"

        changed += 1
    return changed

def apply_to_file(path: Path, specs: dict, cfg: dict) -> None:
    rows, fields = load_csv(path)
    if not rows:
        print(f"[WARN] Missing or empty: {path}")
        return
    fields = ensure_fields(fields, [
        "pip_size","pip_value_quote_per_std_lot","pip_value_account_per_std_lot",
        "min_lot","lot_step"
    ])
    n = apply_to_rows(rows, fields, specs, cfg)
    if n:
        write_csv(path, rows, fields)
    else:
        print(f"[INFO] No index rows updated in {path.name}")

def main():
    cfg   = load_json(CONF)
    specs = load_json(IDX)
    if not specs:
        print(f"[WARN] Missing or empty: {IDX}")
        return
    for p in (SPEC, PLAN):
        apply_to_file(p, specs, cfg)

if __name__ == "__main__":
    main()
