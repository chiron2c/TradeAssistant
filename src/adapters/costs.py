# src/adapters/costs.py
from __future__ import annotations
from typing import Tuple
import pandas as pd
import math

# --- simple helpers ---------------------------------------------------------

def round_to_step(value: float, step: float, mode: str = "floor") -> float:
    """Round value to broker lot step."""
    if step <= 0:
        return value
    n = value / step
    if mode == "ceil":
        n = math.ceil(n + 1e-12)
    elif mode == "nearest":
        n = round(n)
    else:
        n = math.floor(n + 1e-12)
    return n * step


# --- placeholder pip/point value model -------------------------------------
# These are simple, conservative defaults to make sizing workable until we
# read real values from your broker (or from your spec sheet).
#
# * forex  : $10 per "pip" per 1.00 lot    (typical CFD convention)
# * index  : $10 per 1.0 index point per 1.00 lot
# * energy : $10 per 0.01 move per 1.00 lot (e.g., USOIL/UKOIL common in CFDs)
# * metal  : $10 per 0.10 move per 1.00 lot (placeholder, adjust when you have exacts)
#
# If your spec sheet already contains a good value in pip_value_quote_per_std_lot,
# you can keep it; but for consistency we will overwrite it with our placeholder
# so that sizing behaves predictably.

_PIP_VALUE_BY_CLASS = {
    "forex": 10.0,
    "index": 10.0,
    "energy": 10.0,
    "metal": 10.0,
}

def value_per_pip(row: pd.Series) -> float:
    cls = str(row.get("asset_class", "")).strip().lower()
    return _PIP_VALUE_BY_CLASS.get(cls, 10.0)


def spread_cost_in_pips(row: pd.Series) -> float:
    """Round-trip spread cost in pips."""
    try:
        sp = float(row.get("typical_spread", 0) or 0)
    except Exception:
        sp = 0.0
    return float(sp)


def commission_per_round(row: pd.Series) -> float:
    """Commission (quote currency) per round-turn for 1.00 standard lot."""
    try:
        c = float(row.get("commission", 0) or 0)
    except Exception:
        c = 0.0
    return float(c)


# --- public API -------------------------------------------------------------

def enrich_costs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure we have consistent cost columns and a usable pip/point value so the
    sizer can produce tradable positions across asset classes.
    """
    out = df.copy()

    # normalize / overwrite pip value with our placeholder model
    out["pip_value_quote_per_std_lot"] = out.apply(value_per_pip, axis=1).astype(float)

    # cost in pips and quote currency (round-turn) for 1.00 lot
    out["cost_pips_round_turn"] = out.apply(spread_cost_in_pips, axis=1).astype(float)

    # Commission is already in quote currency (round-turn for 1 lot).
    out["cost_quote_round_turn_per_std_lot"] = out.apply(commission_per_round, axis=1).astype(float)

    # (Optional) You could compute a total quote cost proxy here if useful later:
    # out["total_quote_cost_proxy"] = (
    #     out["cost_pips_round_turn"] * out["pip_value_quote_per_std_lot"]
    #     + out["cost_quote_round_turn_per_std_lot"]
    # )

    return out
