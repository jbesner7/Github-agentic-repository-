# Equities Day Trading Playbook

**Status: RELEASED** (owner approved 2026-08-31)

Live `place_*` from **this Cursor chat (Agent F)** still requires an explicit confirm of a **specific** order. This release is not a blanket authorize-all.

Autonomous placing is Agent H, options first, then this playbook as the equity path. Disable the Automation to turn H OFF.

## Locked numbers (copied, not new)

From `config/rules.json` `risk.equity` and `risk.max_open_positions`:

- Stop loss **−20%** of trade cost
- Take profit **+25%** of trade cost
- Size **up to full buying power**, never above it
- Max **one** open position (equity or option — one account-wide slot)
- Broker **stop first** until OCO exists; do not rest a live take-profit

Last verified Agentic buying power (2026-08-30): **$1,500**. Re-read `get_portfolio` before any ticket. Do not hard-code that figure.

## Side — no shorting

- **Long shares only.** Buy to open. Sell only to close those shares.
- **No shorting.** No sell-short. No inverse or leveraged-short ETFs.
- Bearish-only pattern names: **skip**. Puts stay on the options playbook, not this one.

## Session

- Scan and buy **RTH only**: Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`, `market_hours=regular_hours`
- Outside RTH: no scan, no buy
- **Day trade:** no overnight hold. If still open approaching 16:00 ET, sell to flatten in `regular_hours`
- No new entries after **15:45 ET** (time left to place stop / flatten)
- PDT: do **not** throttle day-trade count (owner lock; same as options)

## Universe

- All Robinhood watchlists (same as options)
- Drop crypto (`BTC`, `ETH`, `XRP`, `currency_pair`, `tokenized_stock`)
- Dedupe
- Keep ADV ≥ **2,000,000**
- Account: Agentic ••••2907 only. Never account ending 5638
- Index ETFs (e.g. long SPY / VTI) allowed as **long** shares. Inverse ETFs are not.

## Bias (same patterns, long-only filter)

Locked types: H&S, inverse H&S, double/triple top or bottom, ascending/descending/symmetrical triangle.

- Daily first. Then live quote + **1-minute, 3-minute, 5-minute** (+ hour) **only** on daily hits. 1m = RH `interval=minute`. 5m = `5minute`. 3m is **not** an RH interval — aggregate from 1m. No `15minute`.
- Need a **strict majority bullish** bias
- Tie, mixed, neutral, or bearish → skip this playbook

## Entry ticket

1. `get_equity_tradability` — must be buyable in the regular session. Else skip.
2. Live quote (`get_equity_quotes` / price book). Reject missing or one-sided bid/ask. Do not use a weekend or prior-session print as a live mark.
3. Limit **buy**, `time_in_force=gfd`, `market_hours=regular_hours`. Limit at or inside the **live** ask. Do not chase. Do not use `dollar_amount` / fractional market tickets unless a later approval says so.
4. Whole shares: `shares = floor(buying_power / limit)`. Notional = shares × limit. Must be **≤ buying power**. If shares &lt; 1, skip (cannot afford one share).
5. Always `review_equity_order` then `place_equity_order` with the **same** params. If `order_checks` block: do not place.
6. Max **one** new entry per run. If any open position or working order already exists: **no new entry**.
7. Options first: if a passing option candidate exists this run, do **not** also open an equity day trade.

## After a fill

- Place broker **STOP only**: `stop_market` sell, `stop_price` = **80% of fill**, same share quantity, `regular_hours`. Closest legal stop if the tool rejects the exact tick.
- **No OCO.** Do not rest a live take-profit (double-fill risk).
- Watch **+25%** of cost on later RTH runs in the same session; if live mark is at/through TP, `review_*` + `place_*` **sell** limit of the open shares, then cancel a now-useless stop if it would double-fill.
- Flatten before the close if neither stop nor TP has taken you out.

## Never

- Short stock, inverse ETFs, crypto, options legs, multi-leg, credit spreads
- More than one open position
- Size above buying power
- Invented prices or weekend quotes as live marks
- Extended, overnight, or weekend scan/buy
