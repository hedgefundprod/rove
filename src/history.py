"""
Track previously notified deals to avoid repeating identical pushes.
Stores a JSON file with deal fingerprints (store+product+multiplier).
"""

import json
from datetime import date
from pathlib import Path

from src.valuation import ValuedDeal

HISTORY_FILE = Path(__file__).parent.parent / "data" / "seen_deals.json"

CPP_CHANGE_THRESHOLD = 0.15  # re-notify if CPP changed by more than this


def _deal_key(d: ValuedDeal) -> str:
    dl = d.deal_line
    return f"{dl.store_name}|{dl.product_name}|{dl.multiplier_raw}"


def load_history() -> dict[str, dict]:
    if not HISTORY_FILE.exists():
        return {}
    return json.loads(HISTORY_FILE.read_text())


def save_history(deals: list[ValuedDeal], existing: dict[str, dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    updated = dict(existing)
    for d in deals:
        key = _deal_key(d)
        updated[key] = {"cpp": round(d.cpp, 4), "last_seen": today}
    HISTORY_FILE.write_text(json.dumps(updated, ensure_ascii=False, indent=2))


def split_new_and_seen(
    deals: list[ValuedDeal],
    history: dict[str, dict],
) -> tuple[list[ValuedDeal], list[ValuedDeal]]:
    new, seen = [], []
    for d in deals:
        key = _deal_key(d)
        prev = history.get(key)
        if prev is None or abs(d.cpp - prev["cpp"]) >= CPP_CHANGE_THRESHOLD:
            new.append(d)
        else:
            seen.append(d)
    return new, seen
