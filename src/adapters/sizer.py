# src/adapters/sizer.py
from typing import Dict, Tuple, Optional
import math
import pandas as pd
from adapters.lot import round_to_step

def _to_float(x) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return float(x)
    except Exception:
        return None

def size_row(
    row: pd.Series,
    equity: float,
    risk_pct: float,
    default_stops: Dict[str, float],
    default_min_lot: float,
    default_lot_step: float,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Return (stop_pips_used, risk_amount, lots_suggested, lots_raw)."""
    asset = str(row.get("asset_class") or "").lower()

    stop_pips = _to_float(row.get("stop_pips"))
    if not stop_pips:
        stop_pips = default_stops.get(asset, default_stops.get("forex", 100.0))

    pipval = _to_float(row.get("pip_value_quote_per_std_lot"))
    if pipval is None or not stop_pips or stop_pips <= 0:
        return (stop_pips, None, None, None)

    risk_amt = equity * (risk_pct / 100.0)
    per_std_risk = pipval * stop_pips
    if per_std_risk <= 0:
        return (stop_pips, round(risk_amt, 2), None, None)

    lots_raw = risk_amt / per_std_risk

    min_lot = _to_float(row.get("min_lot")) or default_min_lot
    lot_step = _to_float(row.get("lot_step")) or default_lot_step

    lots_suggested = round_to_step(lots_raw, min_lot, lot_step) if lots_raw > 0 else None
    if lots_suggested and lots_suggested < min_lot:
        lots_suggested = min_lot

    return (
        stop_pips,
        round(risk_amt, 2),
        round(lots_suggested, 2) if lots_suggested is not None else None,
        round(lots_raw, 4) if lots_raw is not None else None,
    )
