# src/adapters/sessions.py
from typing import Optional
import pandas as pd

def _non_empty(s: Optional[str]) -> bool:
    return bool(s and str(s).strip())

def _has_24x5(s: str) -> bool:
    s = (s or "").lower()
    return any(k in s for k in ["24:00", "24h", "24/5", "24x5", "00:00-24:00"])

def enrich_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add simple session flags (asia/london/newyork).
    If hours look 24x5 or blank -> assume all sessions True.
    Otherwise try keywords; if none found -> default True for all.
    """
    out = df.copy()
    hours_col = "hours" if "hours" in out.columns else None

    asia, london, newyork = [], [], []

    for _, row in out.iterrows():
        h = str(row.get(hours_col) or "")
        if not _non_empty(h) or _has_24x5(h):
            asia.append(True); london.append(True); newyork.append(True)
        else:
            low = h.lower()
            a = any(k in low for k in ["tokyo", "asia"])
            l = any(k in low for k in ["london", "uk", "gmt"])
            n = any(k in low for k in ["new york", "ny", "est", "edt"])
            if not (a or l or n):
                a = l = n = True
            asia.append(a); london.append(l); newyork.append(n)

    out["session_asia"] = asia
    out["session_london"] = london
    out["session_newyork"] = newyork
    return out
