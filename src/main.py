#!/usr/bin/env python3
"""
Trade Assistant — Stage 2.5 + Stage 3 (part 3)
- Stage 1: header checks on --dry-run
- Stage 2: parse & normalize → CSV/XLSX
- Stage 2.5: data-quality warnings
- Stage 3: broker enrichment + sessions + cost columns
"""

from pathlib import Path
import argparse
import logging
import sys
import pandas as pd

pd.set_option("display.width", 180)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 40)

ROOT = Path(__file__).resolve().parents[1]
DIRS = {
    "specs": ROOT / "specs",
    "data": ROOT / "data",
    "output": ROOT / "output",
    "logs": ROOT / "logs",
    "config": ROOT / "config",
}
LOG_FILE = DIRS["logs"] / "trade_assistant.log"

OPTIONAL_COLUMNS = {"Spread", "SpreadPoints", "SpreadPips", "Typical Spread (pips)"}
SUGGESTED_COLUMNS = {
    "Symbol (exact in MT4)", "Canonical (friendly)", "Account Type (optional)",
    "Spread Model (Raw-Com / Spread-only)", "Commission (per lot round-turn)",
    "MinLot", "LotStep", "StopLevel (pts)", "FreezeLevel (pts)",
    "Hours (server)", "Notes"
}

def ensure_dirs():
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logging.getLogger().addHandler(console)

def find_spec_files(spec_dir: Path):
    return list(spec_dir.glob("*.csv")) + list(spec_dir.glob("*.xlsx"))

def load_sheet(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)

def validate_columns(df: pd.DataFrame, name: str):
    cols = set(map(str, df.columns))
    missing_suggested = SUGGESTED_COLUMNS - cols
    optional_present = OPTIONAL_COLUMNS & cols
    logging.info(f"[{name}] Columns found: {sorted(cols)}")
    if missing_suggested:
        logging.info(f"[{name}] Missing (suggested only): {sorted(missing_suggested)}")
    if optional_present:
        logging.info(f"[{name}] Optional spread fields present: {sorted(optional_present)}")
    else:
        logging.info(f"[{name}] No spread fields yet — OK for Stage 1.")

def summarize(df: pd.DataFrame, name: str):
    logging.info(f"[{name}] Rows: {len(df)}")
    sample = df.head(5)
    logging.info(f"[{name}] Sample (first 5 rows):\n{sample.to_string(index=False)}")

def stage1_dryrun(spec_dir: Path):
    files = find_spec_files(spec_dir)
    if not files:
        logging.warning(f"No spec sheets found in: {spec_dir}. Add CSV/XLSX and re-run.")
        return
    for f in files:
        try:
            df = load_sheet(f)
            validate_columns(df, f.name)
            summarize(df, f.name)
        except Exception as e:
            logging.exception(f"Error loading {f.name}: {e}")

def stage2_parse_validate_export(spec_dir: Path):
    from specs.parser import parse_specs, to_dataframe, validate_records
    from adapters.broker import enrich as enrich_specs
    from adapters.sessions import enrich_sessions
    from adapters.costs import enrich_costs

    records = parse_specs(spec_dir)
    logging.info(f"Parsed {len(records)} symbols from specs.")

    warnings = validate_records(records)
    if warnings:
        print("\n=== Warnings (data quality) ===")
        for w in warnings:
            print(f" - {w}")
            logging.warning(w)
    else:
        print("\n=== Warnings (data quality) ===\nNone ✅")

    # Base table (Stage 2)
    df = to_dataframe(records)
    print("\n=== Parsed Specs (preview) ===")
    print(df.fillna("").head(20).to_string(index=False))

    out_csv = DIRS["output"] / "specs_summary.csv"
    df.to_csv(out_csv, index=False)
    logging.info(f"Saved summary to {out_csv}")

    out_xlsx = DIRS["output"] / "specs_summary.xlsx"
    try:
        df.to_excel(out_xlsx, index=False)
        logging.info(f"Saved summary to {out_xlsx}")
    except Exception as e:
        logging.warning(f"Could not write Excel summary: {e}")

    # Enriched (Stage 3)
    enr = enrich_specs(records)       # symbols, asset class, pip size/value
    enr = enrich_sessions(enr)        # session flags
    enr = enrich_costs(enr)           # cost_pips / cost_quote

    # Show the key enriched bits
    print("\n=== Enriched Specs (preview) ===")
    cols = [c for c in [
        "symbol_norm","asset_class",
        "typical_spread","commission",
        "cost_pips_round_turn","cost_quote_round_turn_per_std_lot",
        "session_asia","session_london","session_newyork"
    ] if c in enr.columns]
    print(enr.fillna("").loc[:, cols].head(20).to_string(index=False))

    # Save enriched
    enr_csv = DIRS["output"] / "specs_enriched.csv"
    enr_xlsx = DIRS["output"] / "specs_enriched.xlsx"
    enr.to_csv(enr_csv, index=False)
    try:
        enr.to_excel(enr_xlsx, index=False)
    except Exception:
        pass
    logging.info(f"Saved enriched summary to {enr_csv} (+ .xlsx)")

def main():
    parser = argparse.ArgumentParser(description="Trade Assistant Stage 2.5 + Stage 3 (part 3)")
    parser.add_argument("--specs-dir", default=str(DIRS["specs"]), help="Path to specs directory")
    parser.add_argument("--dry-run", action="store_true", help="Header checks only (Stage 1 behavior)")
    args = parser.parse_args()

    ensure_dirs()
    setup_logging()

    logging.info("=== Trade Assistant Stage 2.5/3 — Start ===")
    spec_dir = Path(args.specs_dir)
    if not spec_dir.exists():
        logging.error(f"Specs directory not found: {spec_dir}")
        return 1

    if args.dry_run:
        stage1_dryrun(spec_dir)
        logging.info("Dry run finished — no further actions taken in Stage 1.")
        return 0

    stage2_parse_validate_export(spec_dir)
    logging.info("Stage 2.5/3 — complete ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
