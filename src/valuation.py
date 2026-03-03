"""
Unified CPP (cents per point) calculation for both X-based and flat miles deals.
Only deals with CPP < threshold are worth buying purely for points.
"""

from dataclasses import dataclass

from src.analyzer import DealLine
from src.product_label import estimate_cost


@dataclass
class ValuedDeal:
    deal_line: DealLine
    cpp: float  # cents per point — lower is better
    cpp_source: str  # "multiplier", "est_cost", "product_name", "unknown"
    mile_value_dollars: float  # at 1.5cpp benchmark


def compute_cpp(dl: DealLine) -> tuple[float, str]:
    if dl.multiplier_type == "x":
        if dl.multiplier_value > 0:
            return 100.0 / dl.multiplier_value, "multiplier"
        return float("inf"), "multiplier"

    _cost_str, cost_usd = estimate_cost(dl)
    if cost_usd is not None and cost_usd > 0 and dl.multiplier_value > 0:
        cpp = cost_usd / dl.multiplier_value * 100
        return cpp, "est_cost"

    return float("inf"), "unknown"


def evaluate_deal_lines(lines: list[DealLine]) -> list[ValuedDeal]:
    deals = []
    for dl in lines:
        cpp, source = compute_cpp(dl)
        mile_value = dl.multiplier_value * 1.5 / 100.0 if dl.multiplier_type == "flat_miles" else 0.0
        deals.append(ValuedDeal(
            deal_line=dl,
            cpp=cpp,
            cpp_source=source,
            mile_value_dollars=mile_value,
        ))
    return deals


def filter_under_cpp(deals: list[ValuedDeal], max_cpp: float = 2.0) -> list[ValuedDeal]:
    return sorted(
        [d for d in deals if d.cpp < max_cpp and d.cpp > 0],
        key=lambda d: d.cpp,
    )


def group_by_store(deals: list[ValuedDeal]) -> dict[str, list[ValuedDeal]]:
    groups: dict[str, list[ValuedDeal]] = {}
    for d in deals:
        groups.setdefault(d.deal_line.store_name, []).append(d)
    for v in groups.values():
        v.sort(key=lambda d: d.cpp)
    return groups


if __name__ == "__main__":
    from rich import print as rprint

    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, flatten_deal_lines

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    lines = flatten_deal_lines(stores)
    deals = evaluate_deal_lines(lines)

    good = filter_under_cpp(deals, max_cpp=2.0)
    x_deals = [d for d in good if d.deal_line.multiplier_type == "x"]
    flat_deals = [d for d in good if d.deal_line.multiplier_type == "flat_miles"]

    rprint(f"\n[bold]CPP < 2¢: {len(good)} deals ({len(x_deals)} x-based, {len(flat_deals)} flat)[/bold]")
    for d in good[:20]:
        dl = d.deal_line
        new = " ⚠️新客" if dl.new_customers_only else ""
        rprint(f"  {d.cpp:.2f}¢ | {dl.store_name}{new} | {dl.product_name} | {dl.multiplier_raw}")
