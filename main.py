from datetime import date

from rich.console import Console

from src.ai_summary import build_overview, generate_ai_labels
from src.analyzer import extract_ranked_stores, flatten_deal_lines
from src.api import fetch_shopping_data
from src.notifier import send_notification
from src.product_label import assess_flat_deal, get_label
from src.report import generate_qmd_report
from src.valuation import (
    DealTier,
    TIER_EMOJI,
    ValuedDeal,
    evaluate_deal_lines,
    filter_buy_for_points,
    group_by_store,
)

console = Console()


def main() -> None:
    console.print("[bold blue]Fetching Rove Miles shopping data...[/bold blue]")
    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    deal_lines = flatten_deal_lines(stores)
    all_valued = evaluate_deal_lines(deal_lines)
    console.print(f"[green]{len(stores)} 商户, {len(deal_lines)} 个产品线[/green]")

    x_buy_worthy = filter_buy_for_points(all_valued, min_tier=DealTier.GOOD)

    flat_deals = sorted(
        [d for d in all_valued if d.deal_line.multiplier_type == "flat_miles" and d.mile_value_dollars > 50],
        key=lambda d: d.mile_value_dollars,
        reverse=True,
    )

    flat_good: list[ValuedDeal] = []
    flat_meh: list[ValuedDeal] = []
    flat_skip: list[ValuedDeal] = []
    for d in flat_deals:
        assessment = assess_flat_deal(d.deal_line, d.mile_value_dollars)
        if "💰" in assessment or "👍" in assessment:
            flat_good.append(d)
        elif "❌" in assessment:
            flat_skip.append(d)
        else:
            flat_meh.append(d)

    console.print("[bold blue]Generating AI labels...[/bold blue]")
    all_deal_lines = [d.deal_line for d in x_buy_worthy] + [d.deal_line for d in flat_deals[:15]]
    ai_labels = generate_ai_labels(all_deal_lines)

    overview = build_overview(
        len(stores), len(deal_lines),
        x_buy_worthy, flat_deals, flat_good, flat_skip,
    )
    console.print(f"\n[bold]{overview}[/bold]")

    notification = _format_notification(
        overview, x_buy_worthy, flat_good, flat_meh, flat_skip, ai_labels,
    )
    console.print(f"\n{notification}")

    report_path = generate_qmd_report(
        overview, x_buy_worthy, flat_good, flat_meh, flat_skip, all_valued,
    )
    console.print(f"\n[green]QMD report saved: {report_path}[/green]")

    n_nb = len(group_by_store([d for d in x_buy_worthy if d.tier == DealTier.NO_BRAINER]))
    n_great = len(group_by_store([d for d in x_buy_worthy if d.tier == DealTier.GREAT]))
    priority = "high" if n_nb else "default"
    send_notification(
        notification,
        title=f"Rove 返现 | {n_nb}家闭眼入 {n_great}家划算 {len(flat_good)}个固定里程 | {date.today().isoformat()}",
        tags=["fire", "airplane"],
        priority=priority,
    )
    console.print("[green]Notification sent![/green]")


NTFY_MAX_BYTES = 3800


def _format_notification(
    overview: str,
    x_buy_worthy: list[ValuedDeal],
    flat_good: list[ValuedDeal],
    flat_meh: list[ValuedDeal],
    flat_skip: list[ValuedDeal],
    ai_labels: dict | None,
) -> str:
    today = date.today().isoformat()
    lines = [f"Rove Miles 每日返现监控 {today}", "", overview, ""]

    no_brainers = [d for d in x_buy_worthy if d.tier == DealTier.NO_BRAINER]
    great_only = [d for d in x_buy_worthy if d.tier == DealTier.GREAT]
    good_only = [d for d in x_buy_worthy if d.tier == DealTier.GOOD]

    if no_brainers:
        lines.append("━━ 闭眼入 (返现>80%) ━━")
        _append_x_deals(lines, no_brainers, ai_labels, verbose=True)

    if great_only:
        lines.append("━━ 非常划算 (50-80%) ━━")
        _append_x_deals(lines, great_only, ai_labels, verbose=False, max_stores=8)

    if good_only:
        n = len(group_by_store(good_only))
        lines.append(f"━━ 值得考虑 (30-50%): {n}家商户 ━━")

    if flat_good:
        lines.append("━━ 固定里程 | 值得买 ━━")
        _append_flat_deals_compact(lines, flat_good, ai_labels, max_items=6)

    if flat_skip:
        skip_names = ", ".join(d.deal_line.store_name for d in flat_skip[:5])
        lines.append(f"━━ ❌ 太贵不建议: {skip_names} ━━")

    text = "\n".join(lines)
    if len(text.encode("utf-8")) > NTFY_MAX_BYTES:
        text = text.encode("utf-8")[:NTFY_MAX_BYTES].decode("utf-8", errors="ignore")
        text = text.rsplit("\n", 1)[0] + "\n..."
    return text


def _append_x_deals(
    lines: list[str],
    deals: list[ValuedDeal],
    ai_labels: dict | None,
    *,
    verbose: bool,
    max_stores: int | None = None,
) -> None:
    grouped = group_by_store(deals)
    store_names = list(grouped.keys())
    truncated = 0
    if max_stores and len(store_names) > max_stores:
        truncated = len(store_names) - max_stores
        store_names = store_names[:max_stores]

    for store_name in store_names:
        store_deals = grouped[store_name]
        first = store_deals[0]
        label = _get_ai_or_fallback_label(first.deal_line, ai_labels)
        new_tag = " [仅限新客]" if first.deal_line.new_customers_only else ""

        lines.append(f"• {store_name}{new_tag} — {label}")

        if verbose:
            for d in store_deals:
                emoji = TIER_EMOJI[d.tier]
                lines.append(
                    f"  {emoji} {d.deal_line.product_name}: "
                    f"{d.deal_line.multiplier_raw}倍 → "
                    f"返现{d.effective_return_pct:.0%}, {d.cost_per_mile_cpp:.2f}¢/mi"
                )
            siblings = first.deal_line.other_deal_lines
            lower = [
                s for s in siblings
                if s.multiplier_value > 0
                and s not in [d.deal_line for d in store_deals]
            ]
            if lower:
                others = ", ".join(
                    f"{s.product_name} {s.multiplier_raw}"
                    for s in sorted(lower, key=lambda s: s.multiplier_value, reverse=True)[:3]
                )
                lines.append(f"  ↳ 其他: {others}")
        else:
            best = store_deals[0]
            lines.append(
                f"  {best.deal_line.product_name}: "
                f"{best.deal_line.multiplier_raw}倍 → {best.effective_return_pct:.0%}"
            )
        lines.append("")

    if truncated:
        lines.append(f"  ...还有 {truncated} 家商户\n")


def _append_flat_deals_compact(
    lines: list[str],
    deals: list[ValuedDeal],
    ai_labels: dict | None,
    max_items: int = 8,
) -> None:
    seen_stores: set[str] = set()
    count = 0
    for d in deals:
        if count >= max_items:
            break
        dl = d.deal_line
        if dl.store_name in seen_stores:
            continue
        seen_stores.add(dl.store_name)
        label = _get_ai_or_fallback_label(dl, ai_labels)
        assessment = assess_flat_deal(dl, d.mile_value_dollars)
        short = assessment.split("→")[-1].strip() if "→" in assessment else ""
        new_tag = " [新客]" if dl.new_customers_only else ""
        lines.append(
            f"• {dl.store_name}{new_tag}: "
            f"{dl.multiplier_raw}里程(${d.mile_value_dollars:,.0f}) "
            f"{short}"
        )
        count += 1
    remaining = len(deals) - count
    if remaining > 0:
        lines.append(f"  ...还有 {remaining} 个")
    lines.append("")


def _get_ai_or_fallback_label(dl, ai_labels: dict | None) -> str:
    if ai_labels:
        key = f"{dl.store_name}|{dl.product_name}"
        ai = ai_labels.get(key)
        if ai and ai.get("desc"):
            return ai["desc"]
    return get_label(dl)


if __name__ == "__main__":
    main()
