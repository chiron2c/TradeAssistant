# src/adapters/broker.py
from dataclasses import asdict
from typing import List, Optional, Set
import re
import pandas as pd

# NOTE: absolute import so it works when running "python .\src\main.py"
from specs.models import SymbolSpec

CURRENCIES: Set[str] = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "CNH"}

def _first_token(s: str) -> str:
    s = (s or "").upper().strip()
    # take token before space/paren, keep letters+digits only
    token = re.split(r"[ \t(]", s)[0]
    return re.sub(r"[^A-Z0-9]", "", token)

def normalize_symbol(symbol_mt4: Optional[str], canonical: Optional[str]) -> str:
    # Prefer canonical’s first token if present (e.g., "AUS200 (ASX 200)" -> "AUS200")
    tok = _first_token(canonical) or _first_token(symbol_mt4)
    # Special case from your sheet
    if tok == "GOLD" and (canonical or "").upper().startswith("XAUUSD"):
        tok = "XAUUSD"
    return tok

def asset_class(norm: str) -> str:
    if len(norm) == 6 and norm[:3] in CURRENCIES and norm[3:] in CURRENCIES:
        return "forex"
    if norm in {"US30", "US500", "NAS100", "AUS200", "SPX500"}:
        return "index"
    if norm in {"XAUUSD", "XAGUSD"}:
        return "metal"
    if norm in {"WTI", "BRENT"}:
        return "energy"
    return "other"

def pip_size(norm: str, aclass: str) -> Optional[float]:
    if aclass == "forex":
        # JPY pairs typically quote to 2 decimals; others to 4
        return 0.01 if norm.endswith("JPY") else 0.0001
    return None

def pip_value_per_standard_lot(norm: str, aclass: str) -> Optional[float]:
    # Rule of thumb (quote currency units) for a 100k lot:
    # non-JPY ~ 10.0 per pip; JPY ~ 1000.0 JPY per pip
    if aclass == "forex":
        return 1000.0 if norm.endswith("JPY") else 10.0
    return None

def enrich(records: List[SymbolSpec]) -> pd.DataFrame:
    """Return a DataFrame with extra columns derived for trading logic."""
    rows = []
    for r in records:
        base = asdict(r)
        ns = normalize_symbol(r.symbol_mt4, r.canonical)
        aclass = asset_class(ns)
        base.update({
            "symbol_norm": ns,
            "asset_class": aclass,
            "pip_size": pip_size(ns, aclass),
            "pip_value_quote_per_std_lot": pip_value_per_standard_lot(ns, aclass),
        })
        rows.append(base)

    df = pd.DataFrame(rows)
    # put enriched fields up front
    front = ["symbol_norm", "asset_class", "pip_size", "pip_value_quote_per_std_lot"]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest]
