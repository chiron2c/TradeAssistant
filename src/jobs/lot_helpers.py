# --- src/jobs/lot_helpers.py ---

from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, getcontext
from typing import Dict, Tuple
import re

# Higher precision to avoid float wobble
getcontext().prec = 28

# Defaults across all markets/brokers unless overridden
DEFAULT_MIN_LOT = Decimal("0.01")
DEFAULT_LOT_STEP = Decimal("0.01")

def _norm_symbol(symbol: str) -> str:
    """Normalize symbol to a canonical key used by overrides."""
    s = (symbol or "").upper()
    # unify separators
    s = re.sub(r"[\-_.:/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Map common WTI variants to 'WTI'
    if (
        "WTI" in s
        or "USOIL" in s
        or ("WEST" in s and "TEXAS" in s)
        or ("CRUDE" in s and "WTI" in s)
        or ("WTI" in s and "CASH" in s)
    ):
        return "WTI"

    return s

def _to_dec(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))

def round_to_step(value, step=DEFAULT_LOT_STEP, mode: str = "nearest") -> Decimal:
    """
    Round a value to a given step.
    mode: 'nearest' (banker's), 'down', or 'up'
    """
    v = _to_dec(value)
    st = _to_dec(step)
    if st <= 0:
        raise ValueError("step must be > 0")

    scaled = v / st
    if mode == "down":
        rounded = scaled.to_integral_value(rounding=ROUND_FLOOR) * st
    elif mode == "up":
        rounded = scaled.to_integral_value(rounding=ROUND_CEILING) * st
    elif mode == "nearest":
        nearest = scaled.quantize(Decimal("1"))  # HALF_EVEN by default
        rounded = nearest * st
    else:
        raise ValueError("mode must be 'nearest', 'down', or 'up'")
    return rounded

def clamp_min_lot(value, min_lot=DEFAULT_MIN_LOT) -> Decimal:
    """Ensure the lot is zero or >= min_lot. If >0 but below min_lot, lift to min_lot."""
    v = _to_dec(value)
    ml = _to_dec(min_lot)
    if v <= 0:
        return Decimal("0")
    if v < ml:
        return ml
    return v

# Broker/Symbol-specific overrides
# Keys are (broker_lowercase, normalized_symbol)
BROKER_LOT_OVERRIDES: Dict[Tuple[str, str], Dict[str, Decimal]] = {
    # Exception: CMC WTI min lot is 0.02 (Pepperstone stays 0.01)
    ("cmc", "WTI"): {
        "min_lot": Decimal("0.02"),
        "lot_step": DEFAULT_LOT_STEP,
    },
    # Add more overrides as needed
    # ("pepperstone", "WTI"): {"min_lot": Decimal("0.01"), "lot_step": Decimal("0.01")},
}

def get_lot_rules(broker: str, symbol: str) -> Tuple[Decimal, Decimal]:
    b = (broker or "").strip().lower()
    s = _norm_symbol(symbol or "")
    ov = BROKER_LOT_OVERRIDES.get((b, s), {})
    min_lot = _to_dec(ov.get("min_lot", DEFAULT_MIN_LOT))
    lot_step = _to_dec(ov.get("lot_step", DEFAULT_LOT_STEP))
    return min_lot, lot_step

def normalize_lot_size(requested_lot, broker: str, symbol: str, mode: str = "nearest") -> Decimal:
    """
    Convert a user-requested lot to a broker/symbol-compliant lot:
      1) Round to lot_step (nearest/down/up)
      2) Enforce min_lot unless the request is <= 0 (then return 0)
    """
    min_lot, lot_step = get_lot_rules(broker, symbol)
    stepped = round_to_step(requested_lot, step=lot_step, mode=mode)
    final = clamp_min_lot(stepped, min_lot=min_lot)
    return final
