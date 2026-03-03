import json
import logging
import os

from openai import OpenAI

from src.analyzer import DealLine
from src.product_label import assess_flat_deal, get_label
from src.valuation import ValuedDeal, group_by_store

log = logging.getLogger(__name__)

LABELER_PROMPT = """\
你是一个购物返现分析师。用户通过 Rove Miles 购物门户获得 Capital One 里程。
对于每个商品/服务，请用中文简要说明：
1. 这个商品/服务具体是什么（10-20字）
2. 对于固定里程返现项目：估算产品大致价格区间，判断是否值得纯买点数

回复格式为 JSON 数组，每个元素:
{"key": "商户名|产品名", "desc": "中文描述", "cost": "估算价格", "verdict": "划算/一般/太贵"}

只需回复 JSON，不要其他内容。"""


def generate_ai_labels(deal_lines: list[DealLine]) -> dict[str, dict] | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    items = []
    for dl in deal_lines[:40]:
        desc_snippet = (dl.store_description or "")[:100]
        items.append(f"- {dl.store_name} | {dl.product_name} | "
                     f"category: {dl.store_category} | {desc_snippet}")

    user_msg = "以下是今天的返现商品列表:\n" + "\n".join(items)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": LABELER_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
        return {item["key"]: item for item in parsed}
    except Exception as e:
        log.warning(f"AI labeling failed: {e}")
        return None


def build_overview(
    total_stores: int,
    total_lines: int,
    x_buy_worthy: list[ValuedDeal],
    flat_deals: list[ValuedDeal],
    flat_good: list[ValuedDeal],
    flat_skip: list[ValuedDeal],
) -> str:
    n_nb = len([d for d in x_buy_worthy if d.tier.value == "NO_BRAINER"])
    n_great = len([d for d in x_buy_worthy if d.tier.value == "GREAT"])
    n_good = len([d for d in x_buy_worthy if d.tier.value == "GOOD"])
    nb_stores = len(group_by_store([d for d in x_buy_worthy if d.tier.value == "NO_BRAINER"]))
    great_stores = len(group_by_store([d for d in x_buy_worthy if d.tier.value == "GREAT"]))

    parts = [f"今日监控{total_stores}家商户{total_lines}个产品线。"]

    if n_nb:
        best = [d for d in x_buy_worthy if d.tier.value == "NO_BRAINER"][0]
        dl = best.deal_line
        parts.append(
            f"倍率返现: {nb_stores}家闭眼入(>80%)、{great_stores}家非常划算(50-80%)、"
            f"{n_good}个值得考虑，"
            f"最高 {dl.store_name} {dl.product_name} {dl.multiplier_raw}倍"
            f"(花$100拿~${best.effective_return_pct * 100:.0f}里程价值)。"
        )

    if flat_deals:
        best_flat = flat_deals[0]
        parts.append(
            f"固定里程: {len(flat_deals)}个产品线，"
            f"最高 {best_flat.deal_line.store_name} {best_flat.deal_line.multiplier_raw}里程"
            f"(≈${best_flat.mile_value_dollars:,.0f})。"
        )
        if flat_good:
            parts.append(f"其中{len(flat_good)}个性价比不错。")
        if flat_skip:
            parts.append(f"⚠️ {len(flat_skip)}个产品太贵不建议纯买点数。")

    return "".join(parts)


if __name__ == "__main__":
    from src.api import fetch_shopping_data
    from src.analyzer import extract_ranked_stores, flatten_deal_lines
    from src.valuation import evaluate_deal_lines, filter_buy_for_points

    data = fetch_shopping_data()
    stores = extract_ranked_stores(data)
    lines = flatten_deal_lines(stores)
    valued = evaluate_deal_lines(lines)
    buy_worthy = filter_buy_for_points(valued)
    flat = [d for d in valued if d.deal_line.multiplier_type == "flat_miles" and d.mile_value_dollars > 100]

    overview = build_overview(
        len(stores), len(lines), buy_worthy, flat, [], []
    )
    print(overview)
    print()

    labels = generate_ai_labels([d.deal_line for d in buy_worthy[:10]])
    if labels:
        for k, v in labels.items():
            print(f"  {k}: {v}")
    else:
        print("  (AI unavailable, using fallback labels)")
