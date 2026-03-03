# Rove Miles Cashback Monitor

Daily monitor that tracks the highest cashback multiplier deals on [Rove Miles](https://www.rovemiles.com/) shopping portal and sends push notifications via [ntfy](https://ntfy.sh).

## Features

- Fetches all 1400+ stores from the Rove Miles API
- **Buy-for-Points Analysis**: Identifies deals where buying purely for miles is worthwhile
  - Calculates effective return % and cost-per-mile based on 1.5 cpp valuation
  - Three tiers: 闭眼入 No-Brainer (>80%), 非常划算 Great (50-80%), 值得考虑 Worth It (30-50%)
- Ranks stores by two multiplier types:
  - **X-based multipliers** (e.g., 65.3x) — percentage-style earnings
  - **Flat miles rewards** (e.g., 98,076 miles) — fixed mile amounts per action
- AI-powered daily summary via OpenAI (with template fallback)
- Generates Quarto (`.qmd`) reports for historical tracking
- Push notifications to ntfy with priority escalation for no-brainer deals

## Quick Start

```bash
uv sync
uv run python main.py
```

## Running Individual Modules

Each module can be run standalone for testing:

```bash
uv run python -m src.api         # Test API fetch
uv run python -m src.analyzer    # Test analysis & ranking
uv run python -m src.valuation   # Test buy-for-points analysis
uv run python -m src.notifier    # Send test notification
uv run python -m src.ai_summary  # Test AI summary generation
uv run python -m src.report      # Generate QMD report only
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Enables AI-powered deal summaries (falls back to template) |

## Daily Scheduling

Use cron to run daily:

```bash
# Run at 9am daily
0 9 * * * cd /Users/maxhu/play/rove && uv run python main.py
```

## Project Structure

```
rove/
├── main.py              # Entry point / orchestrator
├── src/
│   ├── api.py           # Rove Miles API client
│   ├── analyzer.py      # Multiplier parsing & ranking
│   ├── valuation.py     # Buy-for-points arbitrage analysis
│   ├── notifier.py      # ntfy push notifications
│   ├── ai_summary.py    # AI-powered deal summaries
│   └── report.py        # QMD report generator
├── reports/             # Generated daily QMD reports
├── pyproject.toml
└── README.md
```
