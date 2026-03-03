from datetime import date
from pathlib import Path

from src.analyzer import RankedStore, build_summary_table
from src.valuation import (
    DealTier,
    ValuedDeal,
    TIER_EMOJI,
    TIER_LABEL,
    filter_buy_for_points,
    format_flat_miles_value,
)

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def generate_qmd_report(
    top_x: list[RankedStore],
    top_flat: list[RankedStore],
    ai_summary: str,
    buy_worthy: list[ValuedDeal] | None = None,
    all_deals: list[ValuedDeal] | None = None,
    report_date: date | None = None,
) -> Path:
    report_date = report_date or date.today()
    REPORTS_DIR.mkdir(exist_ok=True)

    buy_section = _buy_for_points_section(buy_worthy) if buy_worthy else ""
    flat_value_section = _flat_value_section(all_deals) if all_deals else ""

    content = f"""\
---
title: "Rove Miles Cashback Monitor"
subtitle: "Daily Report - {report_date.isoformat()}"
date: "{report_date.isoformat()}"
format:
  html:
    theme: cosmo
    toc: true
  pdf:
    documentclass: article
---

## AI Summary

{ai_summary}

{buy_section}

{flat_value_section}

## Top X-Based Multiplier Deals

{_markdown_table(top_x)}

## Top Flat Miles Rewards

{_markdown_table(top_flat)}

## Raw Data

### X-Based Multipliers

```
{build_summary_table(top_x)}
```

### Flat Miles

```
{build_summary_table(top_flat)}
```
"""

    filepath = REPORTS_DIR / f"rove-{report_date.isoformat()}.qmd"
    filepath.write_text(content)
    return filepath


def _buy_for_points_section(deals: list[ValuedDeal]) -> str:
    no_brainers = [d for d in deals if d.tier == DealTier.NO_BRAINER]
    great = [d for d in deals if d.tier == DealTier.GREAT]
    good = [d for d in deals if d.tier == DealTier.GOOD]

    lines = [
        "## Buy for Points Analysis",
        "",
        f"> Based on 1.5¢/mile valuation (Capital One transfer partners)",
        "",
        f"- **闭眼入 No-Brainer (>80% return):** {len(no_brainers)} deals",
        f"- **非常划算 Great (50-80%):** {len(great)} deals",
        f"- **值得考虑 Worth It (30-50%):** {len(good)} deals",
        "",
    ]

    if no_brainers or great:
        lines.append(_valued_deals_md_table(no_brainers + great))

    return "\n".join(lines)


def _flat_value_section(deals: list[ValuedDeal]) -> str:
    flat = sorted(
        [d for d in deals if d.store.multiplier_type == "flat_miles"],
        key=lambda d: d.mile_value_dollars,
        reverse=True,
    )[:10]
    if not flat:
        return ""

    lines = [
        "## Flat Miles Value Estimate",
        "",
        "| Rank | Store | Miles | Est. Value |",
        "|------|-------|-------|------------|",
    ]
    for i, d in enumerate(flat, 1):
        lines.append(
            f"| {i} | [{d.store.name}]({d.store.url}) | "
            f"{d.store.multiplier_raw} | ${d.mile_value_dollars:,.0f} |"
        )
    return "\n".join(lines)


def _valued_deals_md_table(deals: list[ValuedDeal]) -> str:
    lines = [
        "| Tier | Store | Multiplier | Return | Cost/Mile |",
        "|------|-------|-----------|--------|-----------|",
    ]
    for d in deals:
        emoji = TIER_EMOJI[d.tier]
        label = TIER_LABEL[d.tier]
        lines.append(
            f"| {emoji} {label} | [{d.store.name}]({d.store.url}) | "
            f"{d.store.multiplier_raw} | {d.effective_return_pct:.1%} | "
            f"{d.cost_per_mile_cpp:.2f}¢ |"
        )
    return "\n".join(lines)


def _markdown_table(stores: list[RankedStore]) -> str:
    lines = [
        "| Rank | Multiplier | Store | Category |",
        "|------|-----------|-------|----------|",
    ]
    for i, s in enumerate(stores, 1):
        display = f"{s.multiplier_raw} miles" if s.multiplier_type == "flat_miles" else s.multiplier_raw
        lines.append(f"| {i} | {display} | [{s.name}]({s.url}) | {s.category} |")
    return "\n".join(lines)


if __name__ == "__main__":
    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, top_stores
    from src.valuation import evaluate_deals, filter_buy_for_points

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    deals = evaluate_deals(stores)
    buy_worthy = filter_buy_for_points(deals)

    path = generate_qmd_report(
        top_x=top_stores(stores, multiplier_type="x", n=15),
        top_flat=top_stores(stores, multiplier_type="flat_miles", n=15),
        ai_summary="(test summary placeholder)",
        buy_worthy=buy_worthy,
        all_deals=deals,
    )
    print(f"Report generated: {path}")
