from dataclasses import dataclass, field


@dataclass
class RankedStore:
    name: str
    category: str
    multiplier_raw: str
    multiplier_value: float
    multiplier_type: str  # "x" or "flat_miles"
    url: str
    commission_details: list[dict]
    description: str = ""
    item_categories: list[str] | None = None
    specific_terms: str = ""


@dataclass
class DealLine:
    """A single product/tier within a store's commission structure."""
    store_name: str
    store_url: str
    store_category: str
    store_description: str
    store_item_categories: list[str] | None
    product_name: str
    multiplier_raw: str
    multiplier_value: float
    multiplier_type: str  # "x" or "flat_miles"
    new_customers_only: bool = False
    other_deal_lines: list["DealLine"] = field(default_factory=list, repr=False)


def parse_multiplier(raw: str) -> tuple[float, str]:
    cleaned = str(raw).strip()
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
                    description=item.get("description", ""),
                    item_categories=item.get("categories"),
                    specific_terms=item.get("specific_terms") or "",
                )
            )
    return stores


def flatten_deal_lines(stores: list[RankedStore]) -> list[DealLine]:
    lines: list[DealLine] = []
    for store in stores:
        new_only = _is_new_customers_only(store)

        if not store.commission_details:
            lines.append(DealLine(
                store_name=store.name,
                store_url=store.url,
                store_category=store.category,
                store_description=store.description,
                store_item_categories=store.item_categories,
                product_name="(全部商品)",
                multiplier_raw=store.multiplier_raw,
                multiplier_value=store.multiplier_value,
                multiplier_type=store.multiplier_type,
                new_customers_only=new_only,
            ))
            continue

        store_lines: list[DealLine] = []
        for detail in store.commission_details:
            raw = str(detail["multiplier"])
            value, mtype = parse_multiplier(raw)

            is_zero = value == 0
            detail_new_only = _detail_is_existing_customers(detail["name"])

            if is_zero and detail_new_only:
                continue

            store_lines.append(DealLine(
                store_name=store.name,
                store_url=store.url,
                store_category=store.category,
                store_description=store.description,
                store_item_categories=store.item_categories,
                product_name=detail["name"],
                multiplier_raw=raw,
                multiplier_value=value,
                multiplier_type=mtype,
                new_customers_only=new_only or detail_new_only,
            ))

        for line in store_lines:
            line.other_deal_lines = [l for l in store_lines if l is not line]

        lines.extend(store_lines)

    return lines


def _is_new_customers_only(store: RankedStore) -> bool:
    terms = store.specific_terms.lower()
    if "new customer" in terms or "only new" in terms:
        return True
    for detail in store.commission_details:
        name = detail.get("name", "").lower()
        mult = str(detail.get("multiplier", ""))
        if "existing" in name and (mult == "0" or mult == "0x"):
            return True
    return False


def _detail_is_existing_customers(name: str) -> bool:
    return "existing" in name.lower()


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
    deal_lines = flatten_deal_lines(stores)

    rprint(f"\nTotal stores: {len(stores)}, Total deal lines: {len(deal_lines)}")

    x_lines = [l for l in deal_lines if l.multiplier_type == "x"]
    x_lines.sort(key=lambda l: l.multiplier_value, reverse=True)
    rprint("\n[bold]Top 15 Deal Lines (X-based):[/bold]")
    for i, dl in enumerate(x_lines[:15], 1):
        new = " ⚠️新客" if dl.new_customers_only else ""
        rprint(f"  {i:>2}. {dl.store_name} → {dl.product_name}: {dl.multiplier_raw}{new}")
