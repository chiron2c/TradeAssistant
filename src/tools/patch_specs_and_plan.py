# --- src/tools/patch_specs_and_plan.py ---
# Purpose: Fix missing/misaligned pip values for energy symbols (WTI, BRENT)
# in output/specs_enriched.csv and (optionally) output/plan_preview.csv.
# This sets:
#   pip_size = 0.01
#   pip_value_quote_per_std_lot = 10  (USD accounts; adjust later if acct ccy differs)
#
# Safe to run multiple times (idempotent). Prints a before/after log.

from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]  # C:\Dev\TradeAssistant
OUT = ROOT / "output"
SPEC_PATH = OUT / "specs_enriched.csv"
PLAN_PATH = OUT / "plan_preview.csv"

TARGETS = [
    # Any row whose symbol_norm (or symbol?) contains one of these tokens
    {
        "name": "WTI",
        "match_tokens": ["WTI", "USOIL"],
        "pip_size": "0.01",
        "pip_value_quote_per_std_lot": "10",
    },
    {
        "name": "BRENT",
        "match_tokens": ["BRENT"],
        "pip_size": "0.01",
        "pip_value_quote_per_std_lot": "10",
    },
]

def _load_csv(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    if not path.exists():
        print(f"[WARN] File not found: {path}")
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fieldnames = r.fieldnames or []
    return rows, fieldnames

def _write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    if not rows:
        print(f"[INFO] Nothing to write for {path.name}")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"[DONE] Wrote {len(rows)} rows -> {path}")

def _find_symbol_key(row: Dict[str, str]) -> str:
    # Prefer symbol_norm, else symbol, else empty
    for k in ("symbol_norm", "symbol"):
        if k in row and row[k]:
            return k
    return "symbol_norm"  # default if missing

def _matches(row: Dict[str, str], tokens: List[str]) -> bool:
    key = _find_symbol_key(row)
    v = (row.get(key) or "").upper()
    return any(tok.upper() in v for tok in tokens)

def _ensure_fields(fieldnames: List[str], required: List[str]) -> List[str]:
    new_fields = list(fieldnames)
    for f in required:
        if f not in new_fields:
            new_fields.append(f)
    return new_fields

def _patch_rows(rows: List[Dict[str, str]], fieldnames: List[str], label: str) -> Tuple[List[Dict[str, str]], bool]:
    changed = False
    # Make sure required columns exist
    required = ["pip_size", "pip_value_quote_per_std_lot"]
    fieldnames = _ensure_fields(fieldnames, required)

    for row in rows:
        for tgt in TARGETS:
            if _matches(row, tgt["match_tokens"]):
                before = (row.get("pip_size", ""), row.get("pip_value_quote_per_std_lot", ""))
                # Fill only if empty/invalid (keep non-empty numeric values)
                # If the file was misaligned, these may be empty strings.
                if not (row.get("pip_size") or "").strip():
                    row["pip_size"] = tgt["pip_size"]
                if not (row.get("pip_value_quote_per_std_lot") or "").strip():
                    row["pip_value_quote_per_std_lot"] = tgt["pip_value_quote_per_std_lot"]
                after = (row.get("pip_size", ""), row.get("pip_value_quote_per_std_lot", ""))
                if before != after:
                    print(f"[{label}] {tgt['name']}: pip_size {before[0]!r} -> {after[0]!r}; "
                          f"pip_value {before[1]!r} -> {after[1]!r}")
                    changed = True
    return fieldnames, changed

def main():
    # Patch specs_enriched.csv
    spec_rows, spec_fields = _load_csv(SPEC_PATH)
    if spec_rows:
        spec_fields, spec_changed = _patch_rows(spec_rows, spec_fields, "specs")
        if spec_changed:
            _write_csv(SPEC_PATH, spec_rows, spec_fields)
        else:
            print("[specs] No changes needed.")
    else:
        print("[specs] Skipped (file missing or empty)")

    # Patch plan_preview.csv (if present) so you can verify immediately
    plan_rows, plan_fields = _load_csv(PLAN_PATH)
    if plan_rows:
        plan_fields, plan_changed = _patch_rows(plan_rows, plan_fields, "plan")
        if plan_changed:
            _write_csv(PLAN_PATH, plan_rows, plan_fields)
        else:
            print("[plan] No changes needed.")
    else:
        print("[plan] Skipped (file missing or empty)")

if __name__ == "__main__":
    main()
