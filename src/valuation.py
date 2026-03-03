"""
Points arbitrage analysis at the product level using commission_details.

Each store may have multiple product tiers with different multipliers.
We evaluate each tier independently to give accurate buy-for-points advice.
"""

from dataclasses import dataclass
from enum import Enum

from src.analyzer import DealLine

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

TIER_LABEL_CN = {
    DealTier.NO_BRAINER: "闭眼入",
    DealTier.GREAT: "非常划算",
    DealTier.GOOD: "值得考虑",
    DealTier.NORMAL: "",
}


@dataclass
class ValuedDeal:
    deal_line: DealLine
    cost_per_mile_cpp: float
    effective_return_pct: float
    mile_value_dollars: float
    tier: DealTier


def classify_tier(effective_return: float) -> DealTier:
    for tier, threshold in TIER_THRESHOLDS.items():
        if effective_return >= threshold:
            return tier
    return DealTier.NORMAL


def evaluate_deal_lines(
    lines: list[DealLine],
    mile_value_cpp: float = DEFAULT_MILE_VALUE_CPP,
) -> list[ValuedDeal]:
    deals = []
    for dl in lines:
        if dl.multiplier_type == "x":
            cpp = 100.0 / dl.multiplier_value if dl.multiplier_value > 0 else float("inf")
            effective_return = dl.multiplier_value * mile_value_cpp / 100.0
            mile_value_dollars = 0.0
        else:
            cpp = 0.0
            effective_return = 0.0
            mile_value_dollars = dl.multiplier_value * mile_value_cpp / 100.0

        deals.append(ValuedDeal(
            deal_line=dl,
            cost_per_mile_cpp=cpp,
            effective_return_pct=effective_return,
            mile_value_dollars=mile_value_dollars,
            tier=classify_tier(effective_return),
        ))
    return deals


def filter_buy_for_points(
    deals: list[ValuedDeal],
    min_tier: DealTier = DealTier.GOOD,
) -> list[ValuedDeal]:
    tier_order = [DealTier.NO_BRAINER, DealTier.GREAT, DealTier.GOOD, DealTier.NORMAL]
    min_idx = tier_order.index(min_tier)
    qualifying = [d for d in deals if tier_order.index(d.tier) <= min_idx]
    return sorted(qualifying, key=lambda d: d.effective_return_pct, reverse=True)


def group_by_store(deals: list[ValuedDeal]) -> dict[str, list[ValuedDeal]]:
    groups: dict[str, list[ValuedDeal]] = {}
    for d in deals:
        key = d.deal_line.store_name
        groups.setdefault(key, []).append(d)
    for lines in groups.values():
        lines.sort(key=lambda d: d.effective_return_pct, reverse=True)
    return groups


if __name__ == "__main__":
    from rich import print as rprint

    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, flatten_deal_lines

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    lines = flatten_deal_lines(stores)
    deals = evaluate_deal_lines(lines)

    buy_worthy = filter_buy_for_points(deals)
    rprint(f"\n[bold]Buy-for-Points Deal Lines ({len(buy_worthy)} found):[/bold]")

    grouped = group_by_store(buy_worthy)
    for store_name, store_deals in list(grouped.items())[:10]:
        best = store_deals[0]
        new = " ⚠️新客" if best.deal_line.new_customers_only else ""
        rprint(f"\n[bold]{store_name}[/bold]{new}")
        for d in store_deals:
            emoji = TIER_EMOJI[d.tier]
            rprint(
                f"  {emoji} {d.deal_line.product_name}: "
                f"{d.deal_line.multiplier_raw} → "
                f"返现{d.effective_return_pct:.0%} | {d.cost_per_mile_cpp:.2f}¢/mi"
            )
