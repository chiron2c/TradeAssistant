# src/tools/sanity_checks.py
from pathlib import Path
import sys
import pandas as pd

# --- Make sure we can import siblings under src/ (e.g., adapters) ---
HERE = Path(__file__).resolve()
SRC = HERE.parents[1]  # .../src
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 1) Lot rounding tests
from adapters.lot import round_to_step

print("=== Lot rounding tests ===")
tests = [
    (0.03, 0.01, 0.01),
    (0.034, 0.01, 0.01),
    (0.009, 0.01, 0.01),
    (0.51, 0.10, 0.10),
]
for size, min_lot, step in tests:
    print(f"size={size} min_lot={min_lot} step={step} -> {round_to_step(size, min_lot, step)}")

# 2) Cost sanity test for a forex pair (EURUSD by default)
print("\n=== Cost sanity test (simulate one row) ===")
enriched_path = SRC.parent / "output" / "specs_enriched.csv"
if enriched_path.exists():
    df = pd.read_csv(enriched_path)
else:
    print("Enriched file not found; using defaults.")
    df = pd.DataFrame(columns=["symbol_norm","asset_class","pip_value_quote_per_std_lot"])

row = df[df.get("symbol_norm","")=="EURUSD"].head(1)
if row.empty:
    pip_val = 10.0  # typical FX pip value per std lot for non-JPY pairs
else:
    pip_val = float(row.iloc[0].get("pip_value_quote_per_std_lot") or 10.0)

spread = 1.2       # pips (simulated)
commission = 7.0   # quote-currency per round-turn (simulated)

cost_pips  = spread + (commission / pip_val)
cost_quote = cost_pips * pip_val

print(f"Using pip_value_quote_per_std_lot = {pip_val}")
print(f"spread={spread} pips, commission={commission} ->")
print(f"round-turn cost = {cost_pips:.4f} pips  (~ {cost_quote:.2f} in quote currency)")
