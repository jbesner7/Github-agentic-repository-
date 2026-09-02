# Chart Pattern Playbook (Phase 1/2)

Status: **ACTIVE for signal detection heuristics** (refine anytime).

## Timeframes
- **Live quote** (`get_equity_quotes`)
- **1-minute** — Robinhood `interval=minute` (not `1minute`)
- **3-minute** — not a Robinhood interval; aggregate 1-minute bars with `pipeline.bars.aggregate_to_minutes(..., 3)`
- **5-minute** — Robinhood `interval=5minute`
- **1-hour** — Robinhood `interval=hour`
- **Daily** — Robinhood `interval=day`

Robinhood MCP has no `3minute` and no `15minute`. Do not pass those strings to `get_equity_historicals`.

## Patterns
1. Head and shoulders (bearish)
2. Inverse head and shoulders (bullish)
3. Double top (bearish)
4. Triple top (bearish)
5. Double bottom (bullish)
6. Triple bottom (bullish)
7. Ascending triangle (bullish bias)
8. Descending triangle (bearish bias)
9. Symmetrical triangle (neutral)

## Detection notes
- Implemented as deterministic OHLCV heuristics in `pipeline/patterns.py`.
- Dominant bias requires a strict majority of bullish vs bearish hits across timeframes.
- Neutral-only or bearish results → no long-share day trade. Bearish goes to the options put path. Neutral → skip.
