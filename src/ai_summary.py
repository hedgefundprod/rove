import json
import logging
import os

from openai import OpenAI

from src.analyzer import DealLine
from src.product_label import get_label
from src.valuation import ValuedDeal, group_by_store

log = logging.getLogger(__name__)

FORMATTER_PROMPT = """\
你是一个购物返现分析师，帮用户整理 Rove Miles (Capital One 里程) 买点数的deals。
用户会给你今日筛选后的数据（全部 CPP < 2¢/mi），请用 **Markdown** 格式化成一条清晰的通知。

规则:
- 开头用 1-2 句话总结今日情况
- 倍率返现和固定里程各一个section，用 **加粗** 标注商户名和CPP
- 每个deal一行，格式紧凑，包含: 商户、CPP、倍率/里程数、中文简述商品/服务
- 新客限制用 ⚠️ 标注
- 多个产品线的商户，子产品缩进显示
- 最后可以加一句简短点评（哪些最值得关注）
- 全部用中文，控制在 3000 字节以内
- 不要用表格，用列表格式
- 不要编造数据，只用提供的数据"""


def format_notification_md(
    total_stores: int,
    total_lines: int,
    x_good: list[ValuedDeal],
    flat_good: list[ValuedDeal],
) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    data_lines = _build_data_block(x_good, flat_good)
    user_msg = (
        f"今日数据: {total_stores}家商户, {total_lines}个产品线\n"
        f"筛选后 CPP < 2¢ 共 {len(x_good) + len(flat_good)} 个deal\n\n"
        f"{data_lines}"
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": FORMATTER_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=2000,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"AI formatting failed: {e}")
        return None


def _build_data_block(x_good: list[ValuedDeal], flat_good: list[ValuedDeal]) -> str:
    lines = []

    if x_good:
        lines.append("## 倍率返现")
        for store_name, deals in group_by_store(x_good).items():
            best = deals[0]
            dl = best.deal_line
            label = get_label(dl)
            new = " [仅新客]" if dl.new_customers_only else ""
            lines.append(f"- {store_name}{new}: {best.cpp:.2f}¢/mi, {dl.multiplier_raw}倍, {label}")
            for d in deals[1:]:
                lines.append(f"  - {d.deal_line.product_name}: {d.cpp:.2f}¢/mi, {d.deal_line.multiplier_raw}倍")

    if flat_good:
        lines.append("## 固定里程")
        for store_name, deals in group_by_store(flat_good).items():
            best = deals[0]
            dl = best.deal_line
            label = get_label(dl)
            new = " [仅新客]" if dl.new_customers_only else ""
            lines.append(f"- {store_name}{new}: {best.cpp:.2f}¢/mi, {dl.multiplier_raw}里程, {label}")
            if dl.product_name != "(全部商品)":
                lines.append(f"  - 产品: {dl.product_name}")

    return "\n".join(lines)


def fallback_notification(
    total_stores: int,
    total_lines: int,
    x_good: list[ValuedDeal],
    flat_good: list[ValuedDeal],
) -> str:
    """Plain-text fallback when AI is unavailable."""
    lines = [
        f"📊 今日监控 **{total_stores}** 家商户 **{total_lines}** 个产品线",
        f"筛选 CPP < 2¢: **{len(x_good)}** 倍率 + **{len(flat_good)}** 固定里程",
        "",
    ]

    if x_good:
        lines.append("### 倍率返现")
        for store_name, deals in group_by_store(x_good).items():
            best = deals[0]
            dl = best.deal_line
            label = get_label(dl)
            new = " ⚠️新客" if dl.new_customers_only else ""
            lines.append(f"- **{store_name}**{new} `{best.cpp:.2f}¢` {dl.multiplier_raw}倍 — {label}")
        lines.append("")

    if flat_good:
        lines.append("### 固定里程")
        for store_name, deals in group_by_store(flat_good).items():
            best = deals[0]
            dl = best.deal_line
            label = get_label(dl)
            new = " ⚠️新客" if dl.new_customers_only else ""
            lines.append(f"- **{store_name}**{new} `{best.cpp:.2f}¢` {dl.multiplier_raw}里程 — {label}")
        lines.append("")

    return "\n".join(lines)
