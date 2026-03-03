from datetime import date

from rich.console import Console

from src.ai_summary import generate_summary
from src.analyzer import build_summary_table, extract_ranked_stores, top_stores
from src.api import fetch_shopping_data
from src.notifier import send_notification
from src.report import generate_qmd_report
from src.valuation import (
    DealTier,
    evaluate_deals,
    filter_buy_for_points,
    format_buy_for_points_table,
    format_flat_miles_value,
)

console = Console()

TOP_N = 10


def main() -> None:
    console.print("[bold blue]Fetching Rove Miles shopping data...[/bold blue]")
    data = fetch_shopping_data()

    stores = extract_ranked_stores(data)
    console.print(f"[green]Loaded {len(stores)} stores across {len(data)} categories[/green]")

    top_x = top_stores(stores, multiplier_type="x", n=TOP_N)
    top_flat = top_stores(stores, multiplier_type="flat_miles", n=TOP_N)

    deals = evaluate_deals(stores)
    no_brainers = filter_buy_for_points(deals, min_tier=DealTier.NO_BRAINER)
    great_deals = filter_buy_for_points(deals, min_tier=DealTier.GREAT)
    all_buy_worthy = filter_buy_for_points(deals, min_tier=DealTier.GOOD)

    console.print(f"\n[bold red]Buy-for-Points Deals: "
                  f"{len(no_brainers)} no-brainers, "
                  f"{len(great_deals)} great, "
                  f"{len(all_buy_worthy)} total[/bold red]")
    console.print(format_buy_for_points_table(all_buy_worthy))

    console.print("\n[bold]Top Flat Miles Value (at 1.5 cpp):[/bold]")
    console.print(format_flat_miles_value(deals))

    console.print("\n[bold blue]Generating AI summary...[/bold blue]")
    ai_summary = generate_summary(top_x, top_flat, all_buy_worthy)
    console.print(f"\n[italic]{ai_summary}[/italic]")

    report_path = generate_qmd_report(top_x, top_flat, ai_summary, all_buy_worthy, deals)
    console.print(f"\n[green]QMD report saved: {report_path}[/green]")

    notification = _format_notification(no_brainers, great_deals, all_buy_worthy, ai_summary)
    console.print("\n[bold blue]Sending ntfy notification...[/bold blue]")

    priority = "high" if no_brainers else "default"
    send_notification(
        notification,
        title=f"Rove Miles - {len(no_brainers)} 闭眼入 / {len(great_deals)} 划算 - {date.today().isoformat()}",
        tags=["fire", "airplane"],
        priority=priority,
    )
    console.print("[green]Notification sent![/green]")


def _format_notification(
    no_brainers: list,
    great_deals: list,
    all_deals: list,
    ai_summary: str,
) -> str:
    lines: list[str] = []

    if no_brainers:
        lines.append("🔥🔥🔥 闭眼入 (>80% return)")
        for d in no_brainers:
            lines.append(
                f"  • {d.store.name} {d.store.multiplier_raw} "
                f"→ {d.effective_return_pct:.0%} return, {d.cost_per_mile_cpp:.2f}¢/mi"
            )

    great_only = [d for d in great_deals if d.tier == DealTier.GREAT]
    if great_only:
        lines.append("\n🔥🔥 非常划算 (50-80% return)")
        for d in great_only[:8]:
            lines.append(
                f"  • {d.store.name} {d.store.multiplier_raw} "
                f"→ {d.effective_return_pct:.0%} return, {d.cost_per_mile_cpp:.2f}¢/mi"
            )

    good_only = [d for d in all_deals if d.tier == DealTier.GOOD]
    if good_only:
        lines.append(f"\n🔥 值得考虑 (30-50% return): {len(good_only)} deals")
        for d in good_only[:5]:
            lines.append(f"  • {d.store.name} {d.store.multiplier_raw} → {d.effective_return_pct:.0%}")
        if len(good_only) > 5:
            lines.append(f"  ... and {len(good_only) - 5} more")

    lines.append(f"\n💡 {ai_summary}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
