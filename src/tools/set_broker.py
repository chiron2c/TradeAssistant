# --- src/tools/set_broker.py ---
from pathlib import Path
import csv
import argparse

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "output" / "plan_preview.csv"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", required=True, help="cmc or pepperstone")
    ap.add_argument("--write-copy", action="store_true")
    args = ap.parse_args()

    if not PLAN.exists():
        print(f"[ERR] Not found: {PLAN}"); return 1

    with PLAN.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r); fields = r.fieldnames or []

    if "broker" not in fields: fields = list(fields) + ["broker"]
    for row in rows: row["broker"] = args.broker.lower()

    with PLAN.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    if args.write_copy:
        out = PLAN.with_name(f"plan_preview_{args.broker.lower()}.csv")
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(rows)
        print(f"[DONE] Wrote copy -> {out}")

    print(f"[DONE] Stamped broker={args.broker.lower()} into {PLAN}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
