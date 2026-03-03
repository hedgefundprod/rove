import logging
import os

from openai import OpenAI

from src.analyzer import RankedStore, build_summary_table
from src.valuation import ValuedDeal, format_buy_for_points_table

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a concise cashback deal analyst for Rove Miles (Capital One miles) shopping portal.
Given today's top deals and "buy for points" analysis, write a brief (3-5 sentence) highlight.
Focus on: which deals are worth buying PURELY for the miles even if you don't need the product,
and explain the value proposition (e.g., "97.9% return means you pay $100 and get ~$98 in miles").
Keep it punchy and useful for a push notification. Write in mixed English/Chinese. No markdown."""


def generate_summary(
    top_x: list[RankedStore],
    top_flat: list[RankedStore],
    buy_worthy: list[ValuedDeal] | None = None,
) -> str:
    x_table = build_summary_table(top_x)
    flat_table = build_summary_table(top_flat)
    buy_table = format_buy_for_points_table(buy_worthy) if buy_worthy else ""

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        ai_text = _call_openai(api_key, x_table, flat_table, buy_table)
        if ai_text:
            return ai_text

    log.warning("AI summary unavailable, using template fallback")
    return _fallback_summary(top_x, top_flat, buy_worthy)


def _call_openai(
    api_key: str, x_table: str, flat_table: str, buy_table: str
) -> str | None:
    user_msg = f"""\
Today's Top X-Based Multiplier Deals:
{x_table}

Today's Top Flat Miles Rewards:
{flat_table}

Buy-for-Points Analysis (deals worth buying purely for miles):
{buy_table}

Write a brief daily highlight focusing on the buy-for-points opportunities."""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        log.warning(f"OpenAI API call failed: {e}")
        return None


def _fallback_summary(
    top_x: list[RankedStore],
    top_flat: list[RankedStore],
    buy_worthy: list[ValuedDeal] | None = None,
) -> str:
    parts = []
    if buy_worthy:
        no_brainers = [d for d in buy_worthy if d.tier.value == "NO_BRAINER"]
        if no_brainers:
            names = ", ".join(d.store.name for d in no_brainers[:3])
            best = no_brainers[0]
            parts.append(
                f"闭眼入: {names} at {best.store.multiplier_raw} "
                f"({best.effective_return_pct:.0%} return, {best.cost_per_mile_cpp:.2f}¢/mi)."
            )
        parts.append(f"共 {len(buy_worthy)} 个值得买点数的 deal。")
    best_flat = top_flat[0] if top_flat else None
    if best_flat:
        parts.append(
            f"Highest flat miles: {best_flat.name} at {best_flat.multiplier_raw} miles."
        )
    return " ".join(parts)


if __name__ == "__main__":
    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, top_stores

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)

    summary = generate_summary(
        top_x=top_stores(stores, multiplier_type="x", n=10),
        top_flat=top_stores(stores, multiplier_type="flat_miles", n=10),
    )
    print(summary)
