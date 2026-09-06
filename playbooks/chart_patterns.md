# Chart Pattern Playbook (Phase 1/2)

Status: **ACTIVE for signal detection heuristics** (refine anytime).

## Timeframes
- Daily: major trend, support/resistance, and chart pattern
- 1-hour: confirm direction; reject conflict with the broader intraday trend
- 10-minute: confirm breakout, volume, retest, and entry trigger (Robinhood MCP has no 15-minute bars)
- Live quote: validate the underlying trigger and price the option immediately before ordering

Agent H hierarchy (do not skip): **daily setup → 1-hour confirmation → completed 10-minute trigger → live quote → option review**. Do not use 1-minute or 3-minute (noise). Do not use 5-minute (unnecessary; can make stateless H runs inconsistent).

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
- Agent H hour confirmation is not a majority vote. `classify_hour_bias` uses completed hour hits only (`bullish` / `bearish` / `mixed` / `none`). `hour_trend` compares the last completed hour close to the median of the last 20 completed hour closes. Both must equal the daily winner.
- Neutral-only or bearish results → no long-share day trade. Bearish goes to the options put path. Neutral → skip.
