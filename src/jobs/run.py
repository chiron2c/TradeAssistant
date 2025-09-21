# --- src/jobs/run.py (FX-aware + config + force-broker + clean reasons) ---

import argparse
import sys
from pathlib import Path
import csv
import json
from typing import Dict, Any, List, Tuple

from lot_helpers import normalize_lot_size, get_lot_rules  # includes CMC WTI = 0.02 override

ROOT = Path(__file__).resolve().parents[2]  # -> C:\Dev\TradeAssistant
OUTPUT_DIR = ROOT / "output"
CONFIG_PATH = ROOT / "config" / "account.json"

def _to_float(x, default=0.0) -> float:
    try:
        if x is None or x == "":
            return float(default)
        return float(x)
    except Exception:
        return float(default)

def choose_broker(row: Dict[str, Any], fallback: str) -> str:
    return (row.get("broker") or fallback or "pepperstone").strip().lower()

def choose_symbol(row: Dict[str, Any]) -> str:
    return (row.get("symbol_norm") or row.get("symbol") or "").strip()

def read_csv(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        print(f"[ERROR] Could not find: {path}", file=sys.stderr)
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[Dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)

def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        # Use utf-8-sig so BOM files load cleanly (Windows PowerShell often writes BOM)
        with CONFIG_PATH.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not read config {CONFIG_PATH}: {e}", file=sys.stderr)
        return {}


def resolve_defaults(broker_key: str, cli_fx: float | None, cli_disable_brent: bool) -> Tuple[float, bool]:
    """
    Select defaults (FX factor & disable_brent):
      Priority: CLI > broker-section > top-level defaults > hard defaults
    """
    cfg = load_config()
    fx = None
    dis = None
    if cfg:
        bsec = (cfg.get("brokers") or {}).get(broker_key, {})
        fx = bsec.get("fx_usd_to_account", None)
        dis = bsec.get("disable_brent", None)
        if fx is None:
            fx = cfg.get("default_fx_usd_to_account", None)
    if cli_fx and cli_fx > 0:
        fx = cli_fx
    if cli_disable_brent:
        dis = True
    if fx is None:
        fx = 1.0
    if dis is None:
        dis = False
    return float(fx), bool(dis)

def _missing_inputs(risk_amount: float, stop_pips: float, pip_value_acct: float) -> List[str]:
    miss = []
    if risk_amount    <= 0.0: miss.append("risk_amount")
    if stop_pips      <= 0.0: miss.append("stop_pips_used")
    if pip_value_acct <= 0.0: miss.append("pip_value_account_per_std_lot")
    return miss

def recalc_row(
    row: Dict[str, Any],
    default_broker: str,
    mode: str,
    assume_wti_pip: float | None,
    fx_usd_to_account: float,
    disable_brent: bool,
    force_broker: str | None
) -> Dict[str, Any]:

    broker = (force_broker or choose_broker(row, default_broker)).lower()
    symbol = choose_symbol(row)
    sym_upper = symbol.upper()

    # Optional: disable BRENT
    if disable_brent and "BRENT" in sym_upper:
        row["allowed_lots"] = "0.00"
        row["reason"] = "disabled"
        row["broker"] = broker
        return row

    # Inputs
    lots_suggested = _to_float(row.get("lots_suggested"), 0.0)
    risk_amount    = _to_float(row.get("risk_amount"), 0.0)
    stop_pips      = _to_float(row.get("stop_pips_used"), 0.0)

    pip_value_quote = _to_float(row.get("pip_value_quote_per_std_lot"), 0.0)
    pip_value_acct  = _to_float(row.get("pip_value_account_per_std_lot"), 0.0)

    # TEMP: if quote pip missing for WTI and user provided an assumption
    if pip_value_quote <= 0.0 and "WTI" in sym_upper and assume_wti_pip and assume_wti_pip > 0:
        pip_value_quote = float(assume_wti_pip)
        row["pip_value_quote_per_std_lot"] = f"{pip_value_quote:.4f}"

    # Derive account-currency pip value if missing
    if pip_value_acct <= 0.0:
        if ("WTI" in sym_upper) or ("BRENT" in sym_upper):
            pip_value_acct = pip_value_quote * (fx_usd_to_account if fx_usd_to_account > 0 else 1.0)
        else:
            pip_value_acct = pip_value_quote
        if pip_value_acct > 0.0:
            row["pip_value_account_per_std_lot"] = f"{pip_value_acct:.6f}"

    # Compute suggestion with account-currency pip value
    computed = False
    if (lots_suggested <= 0.0):
        miss = _missing_inputs(risk_amount, stop_pips, pip_value_acct)
        if not miss:
            lots_suggested = risk_amount / (stop_pips * pip_value_acct)
            row["lots_suggested"] = f"{lots_suggested:.2f}"
            computed = True
        else:
            row["lots_suggested"] = f"{lots_suggested:.2f}"
            row["reason"] = "missing_inputs:" + ",".join(miss)

    # Broker/Symbol rules (min lot & step)
    min_lot, lot_step = get_lot_rules(broker, symbol)
    row["min_lot"]  = f"{float(min_lot):.2f}"
    row["lot_step"] = f"{float(lot_step):.2f}"

    # Normalize from suggested
    allowed = float(normalize_lot_size(lots_suggested, broker=broker, symbol=symbol, mode=mode))
    row["allowed_lots"] = f"{allowed:.2f}"

    # Clean up stale reasons if we successfully computed & allowed > 0
    if computed and allowed > 0.0:
        row["reason"] = ""

    if not row.get("reason"):
        if lots_suggested <= 0.0:
            row["reason"] = "zero_suggested"
        elif allowed <= 0.0 and lots_suggested > 0.0:
            row["reason"] = "lot_too_small"

    # Persist broker (after force if used)
    row["broker"] = broker
    return row

def print_debug(rows: list[Dict[str, Any]], debug_symbol: str):
    if not debug_symbol:
        return
    print(f"\n[DEBUG] Rows matching symbol '{debug_symbol}':")
    hit = False
    for r in rows:
        sym = (r.get("symbol_norm") or r.get("symbol") or "").upper()
        if debug_symbol.upper() in sym:
            hit = True
            print(
                f"  sym={sym:<12} broker={r.get('broker',''):>10} "
                f"risk={r.get('risk_amount',''):>8} stop={r.get('stop_pips_used',''):>6} "
                f"pipv_q={r.get('pip_value_quote_per_std_lot',''):>8} pipv_a={r.get('pip_value_account_per_std_lot',''):>8} "
                f"sugg={r.get('lots_suggested',''):>6} -> min={r.get('min_lot',''):>5} step={r.get('lot_step',''):>5} "
                f"allowed={r.get('allowed_lots',''):>6} reason={r.get('reason','')}"
            )
    if not hit:
        print("  (none)")

def print_sample(rows: list[Dict[str, Any]], n: int = 12) -> None:
    print("\nPreview (first rows after normalization):")
    header = ["symbol_norm","symbol","broker","min_lot","lot_step","lots_suggested","allowed_lots","reason"]
    print(" | ".join(h.ljust(14) for h in header))
    print("-" * (len(header) * 17))
    for row in rows[:n]:
        print(" | ".join((row.get(h,"") or "").ljust(14) for h in header))
    print()

def main():
    p = argparse.ArgumentParser(description="Normalize allowed_lots; compute lots_suggested using account-currency pip value; config-aware; force-broker.")
    p.add_argument("--broker", default="", help="Default broker if not present per-row (e.g., cmc, pepperstone).")
    p.add_argument("--mode", default="nearest", choices=["nearest","down","up"], help="Rounding mode for lot step.")
    p.add_argument("--symbol-debug", default="WTI", help="Symbol substring to debug-print (e.g., WTI, BRENT, GOLD).")
    p.add_argument("--use-top", action="store_true", help="Target output/plan_preview_top.csv instead of output/plan_preview.csv.")
    p.add_argument("--assume-wti-pip", type=float, default=None, help="TEMP: pip value for WTI (quote ccy) if missing (e.g., 10).")
    # Config-backed overrides (optional on CLI)
    p.add_argument("--fx-usd-to-account", type=float, default=None, help="Override USD -> Account FX factor; config used if omitted.")
    p.add_argument("--disable-brent", action="store_true", help="Disable BRENT for this run (reason=disabled).")
    # NEW: force per-row broker
    p.add_argument("--force-broker", type=str, default=None, help="Force broker for all rows (ignores any broker already in CSV).")
    # keep common flags as no-ops
    p.add_argument("--equity", type=float, default=None)
    p.add_argument("--save-equity-state", action="store_true")
    p.add_argument("--stops", default=None)
    args = p.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    preview_name = "plan_preview_top.csv" if args.use_top else "plan_preview.csv"
    preview_csv = OUTPUT_DIR / preview_name

    broker_key = (args.broker or "").lower()
    fx_factor, disable_brent_default = resolve_defaults(broker_key, args.fx_usd_to_account, args.disable_brent)
    print(f"[INFO] Broker={broker_key or '(row)'} | fx_usd_to_account={fx_factor} | disable_brent={disable_brent_default} | force_broker={args.force_broker or ''}")

    rows = read_csv(preview_csv)
    if not rows:
        print(f"[INFO] No rows to process in {preview_csv}.", file=sys.stderr)
        return 0

    rows = [recalc_row(r, args.broker, args.mode, args.assume_wti_pip, fx_factor, disable_brent_default, args.force_broker) for r in rows]
    write_csv(preview_csv, rows)
    print_sample(rows)
    print_debug(rows, args.symbol_debug)

    print(f"[DONE] Updated {preview_csv}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
