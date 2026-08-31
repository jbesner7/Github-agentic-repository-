# Chart Pattern Playbook (Phase 1/2)

Status: **ACTIVE for signal detection heuristics** (refine anytime).

## Timeframes
- 10-minute (Robinhood MCP has no 15-minute bars)
- 1-hour
- Daily

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
