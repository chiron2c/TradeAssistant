# src/adapters/lot.py
from typing import Optional
import math

def round_to_step(size: float,
                  min_lot: Optional[float],
                  lot_step: Optional[float]) -> float:
    """
    Round 'size' to broker rules.
    - Enforce min_lot
    - Floor to the nearest lot_step increment from min_lot
    - 4 dp precision to avoid FP noise (common for FX lot sizes)
    """
    if size is None:
        return 0.0
    if min_lot is None:
        min_lot = 0.01
    if lot_step is None or lot_step <= 0:
        lot_step = 0.01

    if size < min_lot:
        return float(f"{min_lot:.4f}")

    steps = math.floor(((size - min_lot) / lot_step) + 1e-12)
    val = min_lot + steps * lot_step
    return float(f"{val:.4f}")
