# --- src/tools/patch_pip_values.py ---
from __future__ import annotations
import csv, json, re
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "output"
SPEC = OUT / "specs_enriched.csv"
PLAN = OUT / "plan_preview.csv"
CONF = ROOT / "config" / "account.json"

FOREX_RE = re.compile(r"^[A-Z]{6,7}$")  # e.g., EURUSD, USDJPY, XAUUSD etc.

def load_cfg():
    if not CONF.exists():
        return {}
    try:
        return json.loads(CONF.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def load_csv(p: Path) -> Tuple[List[Dict[str,str]], List[str]]:
    if not p.exists(): return [], []
    with p.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f); rows = list(r); fields = r.fieldnames or []
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

def symbol_of(row: Dict[str,str]) -> str:
    return (row.get("symbol_norm") or row.get("symbol") or "").upper()

def asset_class_of(row: Dict[str,str]) -> str:
    return (row.get("asset_class") or "").lower()

def is_forex(row: Dict[str,str]) -> bool:
    ac = asset_class_of(row)
    if ac == "forex": return True
    s = symbol_of(row)
    return bool(FOREX_RE.match(s)) and s not in ("USOIL","WTI","BRENT")

def is_energy(row: Dict[str,str]) -> bool:
    return asset_class_of(row) == "energy" or symbol_of(row) in ("WTI","USOIL","BRENT")

def is_index(row: Dict[str,str]) -> bool:
    return asset_class_of(row) == "index"

def quote_ccy(sym: str) -> str:
    return sym[-3:] if len(sym) >= 6 else "USD"

def patch_row_values(row: Dict[str,str], fx_map: Dict[str,float], disable_indices: bool, label: str) -> bool:
    changed = False
    s = symbol_of(row)

    # Oil (energy) – ensure sane defaults if blank
    if is_energy(row):
        if not (row.get("pip_size") or "").strip():
            row["pip_size"] = "0.01"; changed = True
        if not (row.get("pip_value_quote_per_std_lot") or "").strip():
            row["pip_value_quote_per_std_lot"] = "10"; changed = True

    # FOREX – generic pip values; JPY pairs get 1000 of quote ccy
    if is_forex(row):
        q = (row.get("pip_value_quote_per_std_lot") or "").strip()
        sfx = quote_ccy(s)
        if not q:
            q = "1000" if sfx == "JPY" else "10"
            row["pip_value_quote_per_std_lot"] = q; changed = True
        try: qv = float(q)
        except Exception: qv = 0.0
        factor = float(fx_map.get(sfx, 1.0))
        if qv > 0.0:
            row["pip_value_account_per_std_lot"] = f"{qv * factor:.6f}"; changed = True

    return changed

def patch_file(path: Path, disable_indices: bool) -> None:
    rows, fields = load_csv(path)
    if not rows:
        print(f"[WARN] Missing or empty: {path}"); return
    fields = ensure_fields(fields, ["pip_size","pip_value_quote_per_std_lot","pip_value_account_per_std_lot","reason","allowed_lots","broker"])
    fx_map = (load_cfg().get("fx_map_quote_to_account") or {})
    changes = 0

    for r in rows:
        if patch_row_values(r, fx_map, disable_indices, path.name):
            changes += 1
        # Quiet indices in the PLAN (optional)
        if (disable_indices and (path.name == "plan_preview.csv" or path.name.startswith("plan_"))) and is_index(r):
            r["allowed_lots"] = r.get("allowed_lots") or "0.00"
            r["reason"] = "disabled_index"

    if changes: write_csv(path, rows, fields)
    else: print(f"[INFO] No changes needed in {path.name}")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", choices=["specs","plan"], action="append", required=True)
    ap.add_argument("--disable-indices", action="store_true")
    args = ap.parse_args()

    if "specs" in args.apply: patch_file(SPEC, args.disable_indices)
    if "plan"  in args.apply: patch_file(PLAN, args.disable_indices)

if __name__ == "__main__":
    main()
