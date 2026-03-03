from dataclasses import dataclass


@dataclass
class RankedStore:
    name: str
    category: str
    multiplier_raw: str
    multiplier_value: float
    multiplier_type: str  # "x" or "flat_miles"
    url: str
    commission_details: list[dict]


def parse_multiplier(raw: str) -> tuple[float, str]:
    cleaned = raw.strip()
    if cleaned.endswith("x"):
        return float(cleaned[:-1]), "x"
    return float(cleaned.replace(",", "")), "flat_miles"


def extract_ranked_stores(data: dict) -> list[RankedStore]:
    stores: list[RankedStore] = []
    for category, items in data.items():
        for item in items:
            raw = item["commission"]["multiplier"]
            value, mtype = parse_multiplier(raw)
            stores.append(
                RankedStore(
                    name=item["name"],
                    category=category,
                    multiplier_raw=raw,
                    multiplier_value=value,
                    multiplier_type=mtype,
                    url=item["url"],
                    commission_details=item.get("commission_details", []),
                )
            )
    return stores


def top_stores(
    stores: list[RankedStore],
    *,
    multiplier_type: str | None = None,
    n: int = 10,
) -> list[RankedStore]:
    filtered = stores
    if multiplier_type:
        filtered = [s for s in stores if s.multiplier_type == multiplier_type]
    return sorted(filtered, key=lambda s: s.multiplier_value, reverse=True)[:n]


def build_summary_table(stores: list[RankedStore]) -> str:
    lines = [f"{'Rank':<5} {'Multiplier':>12} {'Store':<30} {'Category'}"]
    lines.append("-" * 75)
    for i, s in enumerate(stores, 1):
        display = f"{s.multiplier_raw} miles" if s.multiplier_type == "flat_miles" else s.multiplier_raw
        lines.append(f"{i:<5} {display:>12} {s.name:<30} {s.category}")
    return "\n".join(lines)


if __name__ == "__main__":
    from rich import print as rprint

    from src.api import fetch_shopping_data

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)

    rprint("\n[bold]Top 10 X-Based Multipliers:[/bold]")
    rprint(build_summary_table(top_stores(stores, multiplier_type="x")))

    rprint("\n[bold]Top 10 Flat Miles Rewards:[/bold]")
    rprint(build_summary_table(top_stores(stores, multiplier_type="flat_miles")))
