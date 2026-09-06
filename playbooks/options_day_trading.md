# Options Day Trading Playbook

**Status: RELEASED** (owner approved 2026-08-30), with **2026-09-06.7 Agent H live-safety locks** (`schema_version` 2026-09-06.7).

Live `place_*` from **this Cursor chat (Agent F)** still requires an explicit confirm of a **specific** order.

Autonomous placing is a **separate** Cursor Automation (Agent H). Owner activated **Agentic AI Bot** on 2026-08-30: https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce. Disable that Automation to turn H OFF. That prompt is the standing place-permission; this chat is not. Cursor may start overlapping H runs; the Git lease on `origin/main` is the concurrency gate. Do not assume a scheduler concurrency setting exists.

Agent H mandate: **long call or long put only** on liquid optionable equities and non-inverse ETFs. No equity fallback. No index options at launch.

## Locked rules

- Long call or long put only (no shorts)
- New entries: hard DTE **2–7** inclusive. **No 0 DTE. No 1 DTE.** Owner only may re-enable, separately per DTE, via a commit on `main` after the evidence bar in `config/rules.json` `agent_h.dte_reenable`. H must never flip those flags
- While overnight holding is disabled, evaluate existing expirations in this order: **4, 5, 6, 7, 3, 2 DTE**. Take the first expiration whose ATM or one-OTM contract passes every gate. Close every position the same day regardless of entry DTE. If overnight is later re-enabled with a verified GTC stop, an updated schema, and an owner-approved change on `main`, evaluate **4–7 DTE only**. This ranking should ultimately be determined by backtesting.
- Strike: ATM = nearest strike to live underlying (no 1% band). Tie: lower strike for calls, higher strike for puts. Require the strike set to bracket spot before naming ATM. Call OTM = exactly one listed strike above ATM. Put OTM = exactly one listed strike below ATM. If ATM fails any contract-level eligibility rule (quote age, bid/ask, sizes, spread, delta, IV, volume, open interest, tick validity, debit cap, fee cap, or buying power), try exactly one OTM. If `review_option_order` `order_checks` block ATM, stop — do not try another contract.
- Delta: call **+0.40 through +0.50**; put **−0.50 through −0.40**. Robinhood quotes only. Do not accept absolute-only or sign-inverted values unless the RH schema explicitly documents that inversion
- Max 1 contract
- Liquidity: valid bid and ask, bid size ≥ 1, ask size ≥ 1, spread prefer ≤ 5%, reject > 10%. Volume ≥ **100**. Open interest ≥ **500**. Quote age ≤ **5 seconds** at review and again immediately before place. Reject missing/stale/nonnumeric Greeks, IV, OI, volume, or timestamp
- Underlying live quote: regular session, ≤5 seconds, positive bid and ask, bid ≤ ask. Bullish call trigger uses the live underlying **ask**. Bearish put trigger uses the live underlying **bid**. Do not describe last or midpoint as executable. Recheck immediately before option review
- IV: reject missing/stale/nonnumeric/nonpositive; reject IV ≥ 150%; 1-OTM only also reject IV ≥ 1.25× same-expiry ATM IV; do not apply that multiple to ATM; fail closed if ATM IV unavailable
- Exits: owner-locked working pair **−20% / +40%**. Broker **stop first** until OCO exists. The stop is **not** guaranteed risk — options can gap
- Protective stop: `type=stop_market`, `time_in_force=gfd`, `position_effect=close`, `side=sell`, `quantity=filled_quantity`. Raw trigger = 80% of average fill, then **round toward the fill** on parsed `min_ticks` (never widen, never infer a tick from the premium). After rounding, the trigger must remain below the live option bid; otherwise do not place a stale stop — begin controlled liquidation. If `min_ticks` is missing or unparseable: `protection_failed`. Verify the broker reports accepted and GFD. Do **not** attempt GTC. Overnight holding is disabled.
- 09:30–09:44:59: do not place a new option stop-market. If a leftover lacks a valid working GFD stop, sell-to-close at the live bid and monitor until flat
- Take-profit: cancel and confirm the working stop first; raw threshold = average fill × 1.40, then round **up** to the next valid tick; trigger only when live **bid** ≥ threshold; initial limit = live bid; one replace after 15s; floor = max(threshold, live bid − 1 tick); never lower below threshold just to fill; cancel the replacement 30 seconds after the initial TP; restore GFD protection for any remainder
- Session:
  - Monitor existing positions from **09:30 ET**
  - **No new option entry before 09:45:00 ET**
  - Practical 10m breakout+retest window is about **13:10–15:45 ET**
  - No new entries after **15:45 ET**
  - Recalculate **current DTE** every run: `(expiration_date − today’s ET calendar date).days`. Never freeze overnight eligibility at entry
  - Expiration day: begin **15:30 ET**, absolute deadline **15:45 ET**. Never hold into expiration day. Do not rely on automatic exercise
  - DTE 1–3: begin flatten **15:40 ET**, flat by **15:45 ET**
  - Overnight holding is **off** (GFD-only stop_market; do not attempt GTC). Flatten every open option by **15:45 ET**
- Forced liquidation: cancel-confirm the stop first; sell at live bid. The one-replacement limit applies to entries and take-profit only — not to mandatory or `protection_failed` liquidation. Repeat cancel-confirm-reconcile-requote every 15s with a new `ref_id` until flat or order entry closes. **Do not restore the stop.** 15:45 is the absolute deadline; journal critical if still open near 16:00. Use `limit` unless a later owner-approved slippage policy says otherwise. Restore a GFD stop only after a failed take-profit, not during flatten.
- Session caps (Agent H):
  - Maximum **two** new entries per trading day
  - Stop new entries after **two** losing trades **or** after **1.0% of BOD NLV** realized loss, whichever first
  - Minimum **30-minute** cooldown after a full exit
  - Never re-enter the same underlying the same day after a stopped-out trade
  - Any leftover equity, option, working entry, or working protective order blocks a new entry
- Cash caps (both must pass on the limit; skip if one contract fails either):
  - Planned loss = debit × 20% **excluding fees**
  - `entry_fee` from review: use valid **positive** `total_fee` only when present. If `total_fee` is $0.00 and any component is > 0: journal `fee_conflict`, no estimate. If `total_fee` is $0.00 and every component is $0.00 or absent: accept zero. Otherwise sum non-overlapping components. Never double-count. Ambiguous, duplicated, negative, or unreadable → fee unavailable
  - Journal which field or components produced `entry_fee` (`fee_conflict` / `fee_unavailable` / `fee_explicit_zero` when those apply)
  - **Every trade:** `planned_loss` ≤ **0.49% of current NLV** **and** `planned_loss + estimated_round_trip_fees` ≤ **0.50% of current NLV**. Positive `entry_fee` uses `estimated_round_trip_fees = 3 × entry_fee`. Missing / conflict / explicit-zero fees count as $0 in the second check
  - After close: daily loss and losing-trade flags use **actual net realized P&L**, not estimated fees
  - Full debit = `option_limit_price × 100` ≤ **2.5% of current NLV**
- H graphs on the underlying stock or ETF, in this order only: **daily setup → 1-hour confirmation → completed 10-minute trigger → live quote → option review**
  - Daily: major trend, support/resistance, and chart pattern. Daily neckline governs the 10m breakout
  - 1-hour: confirm direction mathematically — `classify_hour_bias` and `hour_trend` (last completed hour close vs median of last 20 completed hour closes) must both equal the daily winner; mixed/none/conflict → skip
  - 10-minute: confirm breakout, volume, retest, and entry trigger
  - Live quote: validate the underlying trigger and price the option immediately before ordering
- Pattern math is locked in `rules.json` `agent_h.patterns` and `pipeline/patterns.py`: H&S order and 1.5% head prominence, 3-bar pivot separation, max duration 60 daily / 40 hour bars on every named-pivot pattern including doubles/triples, triangle OLS plus 2 touches/side, overlapping rank is H&S then double/triple then triangle (triangle last-touch, never window end)
- Do **not** use 1-minute or 3-minute charts (too much noise for an autonomous system). Do **not** use a 5-minute chart (unnecessary here; can make stateless runs inconsistent)
- 10m trigger: ≥20 **completed current-session** 10m bars as the lookback (skip — do not mix prior session); breakout close ≥ **0.10%** beyond the daily level; volume ≥ **1.5× median** of prior 20 completed 10m; bullish retest low enters ±0.20% and close finishes above the daily level; bearish retest high enters ±0.20% and close finishes below; a completed close through the level against the trade invalidates; live underlying ask (calls) or bid (puts) ≥ **0.10%** beyond breakout before review
- Earnings / events: do not knowingly enter or hold through an identified earnings or binary event. If required event data are unavailable or ambiguous, do not open and do not carry overnight. Check the entire possible holding interval at entry, not only the next session. Blackout: start of the regular session immediately preceding the scheduled release through the end of the second full regular session after. BMO/AMC/intraday
- Entry: tick-rounded midpoint, never above ask. `max_acceptable_debit` is the **tick-floored** independent cap (min of first live ask, 2.5% NLV, fee ceiling) — **not** the first ticket. One replacement (+1 tick / 30s) **only after cancel-confirm and zero fill**, and **only if** first+1 tick is still ≤ live ask and ≤ that cap; otherwise skip and journal `replacement_skipped_tick_cap`. Cancel at 60s after a terminal cancel/fill reconcile. Re-quote before replace and before place. Never chase above the cap. Never send a same-price replacement.
- Partial fill: protect filled size immediately from broker average fill; cancel the remainder and wait for the terminal cancel state
- If fill succeeds and stop review/place fails: immediate controlled sell-to-close, poll to completion, and journal `protection_failed`
- Re-read buying power immediately before review and before place
- Losing trade = fully closed trade with negative net realized P&L after fees. Break-even is not a loss
- H lease, continuity, Git-independent single closer, fire budget, and the `INV[key]=value` registry: follow `playbooks/agent_h_autonomous.PROMPT.md`. Do not keep a second copy here.
- BOD NLV: prefer a broker beginning-of-day field in `journal/h_session.json`. First-fire `total_value` is `first_fire_baseline_nlv` only. If genuine BOD NLV cannot be established: no new entry
- Exhaust pagination before concluding: no working order, no earlier entry today, no stop-out, strikes bracket spot, or no duplicate account match
- Confirm required MCP tools/fields at the start of RTH work; fail closed if any required capability is missing
- Use Options Watchlist + all other watchlists; no crypto; no index
- PDT: do **not** reduce day-trade frequency (owner lock; owner stated PDT rule no longer exists — not independently verified here)
- Account: Agentic only
