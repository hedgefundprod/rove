from datetime import date

from rich.console import Console

from src.ai_summary import fallback_notification, format_notification_md
from src.analyzer import extract_ranked_stores, flatten_deal_lines
from src.api import fetch_shopping_data
from src.notifier import send_notification
from src.report import generate_qmd_report
from src.valuation import (
    evaluate_deal_lines,
    filter_under_cpp,
)

console = Console()

MAX_CPP = 2.0
NTFY_MAX_BYTES = 3800


def main() -> None:
    console.print("[bold blue]Fetching Rove Miles shopping data...[/bold blue]")
    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    deal_lines = flatten_deal_lines(stores)
    all_valued = evaluate_deal_lines(deal_lines)
    console.print(f"[green]{len(stores)} 商户, {len(deal_lines)} 个产品线[/green]")

    good_deals = filter_under_cpp(all_valued, max_cpp=MAX_CPP)
    x_good = [d for d in good_deals if d.deal_line.multiplier_type == "x"]
    flat_good = [d for d in good_deals if d.deal_line.multiplier_type == "flat_miles"]

    console.print(f"[bold]CPP < {MAX_CPP}¢: {len(x_good)} 倍率 + {len(flat_good)} 固定里程[/bold]")

    console.print("[bold blue]AI formatting notification...[/bold blue]")
    notification = format_notification_md(len(stores), len(deal_lines), x_good, flat_good)
    if not notification:
        console.print("[yellow]AI unavailable, using fallback[/yellow]")
        notification = fallback_notification(len(stores), len(deal_lines), x_good, flat_good)

    if len(notification.encode("utf-8")) > NTFY_MAX_BYTES:
        notification = notification.encode("utf-8")[:NTFY_MAX_BYTES].decode("utf-8", errors="ignore")
        notification = notification.rsplit("\n", 1)[0] + "\n..."

    console.print(f"\n{notification}")

    report_path = generate_qmd_report(
        notification.split("\n")[0], x_good, flat_good, all_valued,
    )
    console.print(f"\n[green]QMD report: {report_path}[/green]")

    priority = "high" if good_deals else "default"
    send_notification(
        notification,
        title=f"Rove 买点数 | {len(good_deals)}个<{MAX_CPP}¢/mi | {date.today().isoformat()}",
        tags=["fire", "airplane"],
        priority=priority,
    )
    console.print("[green]Notification sent![/green]")


if __name__ == "__main__":
    main()
