from datetime import date
from pathlib import Path

from src.product_label import get_label
from src.valuation import ValuedDeal

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def generate_qmd_report(
    overview: str,
    x_good: list[ValuedDeal],
    flat_good: list[ValuedDeal],
    all_deals: list[ValuedDeal],
    report_date: date | None = None,
) -> Path:
    report_date = report_date or date.today()
    REPORTS_DIR.mkdir(exist_ok=True)

    content = f"""\
---
title: "Rove Miles 买点数监控"
subtitle: "{report_date.isoformat()}"
date: "{report_date.isoformat()}"
format:
  html:
    theme: cosmo
    toc: true
---

## 总览

{overview}

{_deals_section("倍率返现", x_good)}

{_deals_section("固定里程", flat_good)}
"""

    filepath = REPORTS_DIR / f"rove-{report_date.isoformat()}.qmd"
    filepath.write_text(content)
    return filepath


def _deals_section(title: str, deals: list[ValuedDeal]) -> str:
    if not deals:
        return ""

    lines = [
        f"## {title} (CPP < 2¢)",
        "",
        "| 商户 | 产品 | 倍数/里程 | CPP | 描述 | 限制 |",
        "|------|------|-----------|-----|------|------|",
    ]
    for d in deals:
        dl = d.deal_line
        label = get_label(dl)
        restriction = "仅新客" if dl.new_customers_only else ""
        lines.append(
            f"| [{dl.store_name}]({dl.store_url}) | {dl.product_name} | "
            f"{dl.multiplier_raw} | {d.cpp:.2f}¢ | {label} | {restriction} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, flatten_deal_lines
    from src.valuation import evaluate_deal_lines, filter_under_cpp

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    lines = flatten_deal_lines(stores)
    deals = evaluate_deal_lines(lines)
    good = filter_under_cpp(deals, max_cpp=2.0)

    x = [d for d in good if d.deal_line.multiplier_type == "x"]
    flat = [d for d in good if d.deal_line.multiplier_type == "flat_miles"]

    path = generate_qmd_report("(test)", x, flat, deals)
    print(f"Report: {path}")
