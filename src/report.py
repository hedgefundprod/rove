from datetime import date
from pathlib import Path

from src.product_label import assess_flat_deal, get_label
from src.valuation import (
    DealTier,
    TIER_EMOJI,
    TIER_LABEL_CN,
    ValuedDeal,
)

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def generate_qmd_report(
    overview: str,
    x_buy_worthy: list[ValuedDeal],
    flat_good: list[ValuedDeal],
    flat_meh: list[ValuedDeal],
    flat_skip: list[ValuedDeal],
    all_deals: list[ValuedDeal],
    report_date: date | None = None,
) -> Path:
    report_date = report_date or date.today()
    REPORTS_DIR.mkdir(exist_ok=True)

    x_section = _x_deals_section(x_buy_worthy)
    flat_section = _flat_deals_section(flat_good, flat_meh, flat_skip)

    content = f"""\
---
title: "Rove Miles 每日返现监控"
subtitle: "{report_date.isoformat()}"
date: "{report_date.isoformat()}"
format:
  html:
    theme: cosmo
    toc: true
---

## 总览

{overview}

{x_section}

{flat_section}
"""

    filepath = REPORTS_DIR / f"rove-{report_date.isoformat()}.qmd"
    filepath.write_text(content)
    return filepath


def _x_deals_section(deals: list[ValuedDeal]) -> str:
    if not deals:
        return ""

    tiers = [
        (DealTier.NO_BRAINER, [d for d in deals if d.tier == DealTier.NO_BRAINER]),
        (DealTier.GREAT, [d for d in deals if d.tier == DealTier.GREAT]),
        (DealTier.GOOD, [d for d in deals if d.tier == DealTier.GOOD]),
    ]

    lines = [
        "## 倍率返现 (X-Based)",
        "",
        "> 基于 1.5¢/里程估值 (Capital One 转航司伙伴)",
        "",
    ]

    for tier, tier_deals in tiers:
        if not tier_deals:
            continue
        emoji = TIER_EMOJI[tier]
        label = TIER_LABEL_CN[tier]
        lines.append(f"### {emoji} {label}")
        lines.append("")
        lines.append("| 商户 | 产品 | 倍数 | 返现率 | ¢/里程 | 限制 |")
        lines.append("|------|------|------|--------|--------|------|")
        for d in tier_deals:
            dl = d.deal_line
            rest = "仅新客" if dl.new_customers_only else ""
            lines.append(
                f"| [{dl.store_name}]({dl.store_url}) | {dl.product_name} | "
                f"{dl.multiplier_raw} | {d.effective_return_pct:.1%} | "
                f"{d.cost_per_mile_cpp:.2f}¢ | {rest} |"
            )
        lines.append("")

    return "\n".join(lines)


def _flat_deals_section(
    good: list[ValuedDeal],
    meh: list[ValuedDeal],
    skip: list[ValuedDeal],
) -> str:
    if not good and not meh and not skip:
        return ""

    lines = ["## 固定里程返现", ""]

    if good:
        lines.append("### 💰 值得买")
        lines.append("")
        _flat_table(lines, good)

    if meh:
        lines.append("### ⚠️ 性价比一般")
        lines.append("")
        _flat_table(lines, meh)

    if skip:
        lines.append("### ❌ 太贵不建议")
        lines.append("")
        _flat_table(lines, skip)

    return "\n".join(lines)


def _flat_table(lines: list[str], deals: list[ValuedDeal]) -> None:
    lines.append("| 商户 | 产品 | 里程 | 里程价值 | 评估 |")
    lines.append("|------|------|------|---------|------|")
    for d in deals:
        dl = d.deal_line
        assessment = assess_flat_deal(dl, d.mile_value_dollars)
        short = assessment.split("→")[-1].strip() if "→" in assessment else assessment
        lines.append(
            f"| [{dl.store_name}]({dl.store_url}) | {dl.product_name} | "
            f"{dl.multiplier_raw} | ${d.mile_value_dollars:,.0f} | {short} |"
        )
    lines.append("")


if __name__ == "__main__":
    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, flatten_deal_lines
    from src.valuation import evaluate_deal_lines, filter_buy_for_points

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    lines = flatten_deal_lines(stores)
    deals = evaluate_deal_lines(lines)

    path = generate_qmd_report(
        "(test overview)",
        filter_buy_for_points(deals),
        [], [], [],
        deals,
    )
    print(f"Report generated: {path}")
