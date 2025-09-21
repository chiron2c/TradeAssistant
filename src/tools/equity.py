from pathlib import Path
import argparse
import yaml

ROOT = Path(__file__).resolve().parents[2]  # .../TradeAssistant
STATE_FILE = ROOT / "data" / "equity_state.yaml"

def load_equity() -> float:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return float(data.get("equity", 0.0))
    except FileNotFoundError:
        return 0.0

def save_equity(value: float) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump({"equity": float(value)}, f, sort_keys=False)

def main():
    ap = argparse.ArgumentParser(description="Get/Set account equity")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--show", action="store_true", help="Show current equity")
    g.add_argument("--set", type=float, help="Set equity to an exact value")
    g.add_argument("--add", type=float, help="Add amount to current equity (can be negative)")
    args = ap.parse_args()

    if args.show:
        print(f"equity={load_equity():.2f}  (file: {STATE_FILE})")
        return

    if args.set is not None:
        save_equity(args.set)
        print(f"equity set -> {args.set:.2f}  (file: {STATE_FILE})")
        return

    if args.add is not None:
        cur = load_equity()
        new_val = cur + args.add
        save_equity(new_val)
        print(f"equity {cur:.2f} + {args.add:.2f} = {new_val:.2f}  (file: {STATE_FILE})")
        return

    # default: show
    print(f"equity={load_equity():.2f}  (file: {STATE_FILE})")

if __name__ == "__main__":
    main()
