"""
Points arbitrage analysis: identify deals where buying purely for miles is worthwhile.

Rove Miles = Capital One miles, transferable to airline partners.
Typical valuations:
  - Cash redemption:    ~1.0 cpp (cents per point)
  - Transfer partners:  ~1.5 cpp (economy sweet spots)
  - Premium redemption: ~2.0 cpp (business/first class sweet spots)

For X-based multipliers (e.g., 65.3x = 65.3 miles per $1):
  - cost_per_mile = 100 / multiplier  (in cents)
  - effective_return = multiplier * mile_value_cpp / 100

Thresholds for "buy for points" alerts:
  - GOOD:       effective return > 30%  (buying miles below retail)
  - GREAT:      effective return > 50%  (half your money back in miles)
  - NO_BRAINER: effective return > 80%  (almost free miles)
"""

from dataclasses import dataclass
from enum import Enum

from src.analyzer import RankedStore

DEFAULT_MILE_VALUE_CPP = 1.5


class DealTier(Enum):
    NO_BRAINER = "NO_BRAINER"
    GREAT = "GREAT"
    GOOD = "GOOD"
    NORMAL = "NORMAL"


TIER_THRESHOLDS = {
    DealTier.NO_BRAINER: 0.80,
    DealTier.GREAT: 0.50,
    DealTier.GOOD: 0.30,
}

TIER_EMOJI = {
    DealTier.NO_BRAINER: "🔥🔥🔥",
    DealTier.GREAT: "🔥🔥",
    DealTier.GOOD: "🔥",
    DealTier.NORMAL: "",
}

TIER_LABEL = {
    DealTier.NO_BRAINER: "闭眼入 (No-Brainer)",
    DealTier.GREAT: "非常划算 (Great Deal)",
    DealTier.GOOD: "值得考虑 (Worth It)",
    DealTier.NORMAL: "",
}


@dataclass
class ValuedDeal:
    store: RankedStore
    cost_per_mile_cpp: float
    effective_return_pct: float
    mile_value_dollars: float
    tier: DealTier


def classify_tier(effective_return: float) -> DealTier:
    for tier, threshold in TIER_THRESHOLDS.items():
        if effective_return >= threshold:
            return tier
    return DealTier.NORMAL


def evaluate_deals(
    stores: list[RankedStore],
    mile_value_cpp: float = DEFAULT_MILE_VALUE_CPP,
) -> list[ValuedDeal]:
    deals = []
    for store in stores:
        if store.multiplier_type == "x":
            cpp = 100.0 / store.multiplier_value if store.multiplier_value > 0 else float("inf")
            effective_return = store.multiplier_value * mile_value_cpp / 100.0
            mile_value_dollars = 0.0
        else:
            cpp = 0.0
            effective_return = 0.0
            mile_value_dollars = store.multiplier_value * mile_value_cpp / 100.0

        deals.append(
            ValuedDeal(
                store=store,
                cost_per_mile_cpp=cpp,
                effective_return_pct=effective_return,
                mile_value_dollars=mile_value_dollars,
                tier=classify_tier(effective_return),
            )
        )
    return deals


def filter_buy_for_points(
    deals: list[ValuedDeal],
    min_tier: DealTier = DealTier.GOOD,
) -> list[ValuedDeal]:
    tier_order = [DealTier.NO_BRAINER, DealTier.GREAT, DealTier.GOOD, DealTier.NORMAL]
    min_idx = tier_order.index(min_tier)
    qualifying = [d for d in deals if tier_order.index(d.tier) <= min_idx]
    return sorted(qualifying, key=lambda d: d.effective_return_pct, reverse=True)


def format_buy_for_points_table(deals: list[ValuedDeal]) -> str:
    lines = [
        f"{'':>3} {'Store':<25} {'Mult':>7} {'Return':>8} {'CPP':>6} {'Tier'}",
        "-" * 72,
    ]
    for i, d in enumerate(deals, 1):
        emoji = TIER_EMOJI[d.tier]
        lines.append(
            f"{i:>3} {d.store.name:<25} "
            f"{d.store.multiplier_raw:>7} "
            f"{d.effective_return_pct:>7.1%} "
            f"{d.cost_per_mile_cpp:>5.2f}¢ "
            f"{emoji} {TIER_LABEL[d.tier]}"
        )
    return "\n".join(lines)


def format_flat_miles_value(deals: list[ValuedDeal]) -> str:
    flat_deals = sorted(
        [d for d in deals if d.store.multiplier_type == "flat_miles"],
        key=lambda d: d.mile_value_dollars,
        reverse=True,
    )
    lines = [
        f"{'':>3} {'Store':<25} {'Miles':>10} {'Value':>10}",
        "-" * 55,
    ]
    for i, d in enumerate(flat_deals[:10], 1):
        lines.append(
            f"{i:>3} {d.store.name:<25} "
            f"{d.store.multiplier_raw:>10} "
            f"${d.mile_value_dollars:>8,.0f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    deals = evaluate_deals(stores)

    from rich import print as rprint

    buy_worthy = filter_buy_for_points(deals)
    rprint(f"\n[bold]Buy-for-Points Deals ({len(buy_worthy)} found):[/bold]")
    rprint(format_buy_for_points_table(buy_worthy))

    rprint("\n[bold]Top Flat Miles Value (at 1.5 cpp):[/bold]")
    rprint(format_flat_miles_value(deals))
