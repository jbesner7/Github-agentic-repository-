# Options Day Trading Playbook

**Status: RELEASED** (owner approved 2026-08-30), with **2026-09-05 Agent H locks**.

Live `place_*` from **this Cursor chat (Agent F)** still requires an explicit confirm of a **specific** order.

Autonomous placing is a **separate** Cursor Automation (Agent H). Owner activated **Agentic AI Bot** on 2026-08-30: https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce. Disable that Automation to turn H OFF. That prompt is the standing place-permission; this chat is not.

Agent H mandate: **long call or long put only** on liquid optionable equities and non-inverse ETFs. No equity fallback. No index options at launch.

## Locked rules

- Long call or long put only (no shorts)
- New entries: DTE **2–7** inclusive. **No 0 DTE. No 1 DTE.** Owner only may re-enable, separately per DTE, via a commit on `main` after the evidence bar in `config/rules.json` `agent_h.dte_reenable`. H must never flip those flags
- Strike: ATM preferred, else 1 OTM
- Delta band: abs(delta) 0.40–0.50 from Robinhood quotes only
- Max 1 contract
- Liquidity: valid bid and ask, bid size ≥ 1, ask size ≥ 1, spread prefer ≤ 5%, reject > 10%. Volume ≥ **100**. Open interest ≥ **500**. Quote age ≤ **5 seconds** at review and again immediately before place. Reject missing/stale/nonnumeric Greeks, IV, OI, volume, or timestamp
- IV: reject missing/stale/nonnumeric/nonpositive; reject IV ≥ 150%; 1-OTM only also reject IV ≥ 1.25× same-expiry ATM IV; do not apply that multiple to ATM; fail closed if ATM IV unavailable
- Exits: owner-locked working pair **−20% / +40%**. Broker **stop first** until OCO exists. The stop is **not** guaranteed risk — options can gap. Overnight, treat **full debit** as possible loss
- Take-profit: threshold = average fill × 1.40; trigger only when live **bid** ≥ threshold; initial limit = live bid; one replace after 15s; floor = max(threshold, live bid − 1 tick); never lower below threshold just to fill
- Session:
  - Monitor existing positions from **09:30 ET**
  - **No new option entry before 09:45:00 ET**
  - No new entries after **15:45 ET**
  - Recalculate **current DTE** every run: `(expiration_date − today’s ET calendar date).days`. Never freeze overnight eligibility at entry
  - Expiration day: target **15:30 ET**, absolute deadline **15:45 ET**. Never hold into expiration day. Do not rely on automatic exercise
  - **Current DTE ≤ 3:** close by **15:45 ET**. No overnight
  - **Current DTE ≥ 4:** overnight permitted with the broker stop, except never through earnings/binary events
- Session caps (Agent H):
  - Maximum **two** new entries per trading day
  - Stop new entries after **two** losing trades **or** after **1.0% of session-start NLV** realized loss, whichever first
  - Minimum **30-minute** cooldown after a full exit
  - Never re-enter the same underlying the same day after a stopped-out trade
  - Any leftover equity, option, working entry, or working protective order blocks a new entry
- Cash caps (both must pass on the limit; skip if one contract fails either):
  - Planned loss = debit × 20% **excluding fees**
  - `planned_loss + estimated_entry_and_exit_fees` ≤ **0.5% of current NLV**; if fees unavailable, `planned_loss` ≤ **0.49% of current NLV**
  - Full debit = `option_limit_price × 100` ≤ **2.5% of current NLV**
  - Losing trades and daily realized loss use **net P&L after all fees and regulatory charges**
- H graphs: **daily** (setup + direction) + **1-hour** (confirmation) + **10-minute** (entry trigger). Do **not** use 1m/3m/5m for Agent H
- 10m trigger: ≥20 **completed current-session** 10m bars (skip — do not mix prior session); breakout close ≥ **0.10%** beyond level; volume ≥ **1.5× median** of prior 20 completed 10m; retest within **0.20%** then close in breakout direction; live last ≥ **0.10%** beyond breakout before review
- Earnings blackout: no entry from the start of the regular session immediately preceding the scheduled release through the end of the second full regular session after. BMO/AMC/intraday. Fail closed if date/time missing, conflicting, or unclear. Also block investor-day, FDA, merger-vote, halt, split, and similar binary events when identified
- Entry: tick-rounded midpoint, never above ask, one replacement (+1 tick / 30s), cancel at 60s, re-quote before replace and before place, never chase above the original max debit
- Partial fill: protect filled size immediately from broker average fill; cancel the remainder
- If fill succeeds and stop review/place fails: immediate controlled sell-to-close and journal `protection_failed`
- Re-read buying power immediately before review and before place
- Losing trade = fully closed trade with negative net realized P&L after fees. Break-even is not a loss
- H lease: `journal/h_lease.json` + automation id `9af478e7-a454-11f1-a7d1-d6b4613131ce`
- Session-start NLV: `journal/h_session.json` written atomically on the first valid RTH fire (`et_trading_date`, `first_valid_rth_timestamp_et`, `account` `••••2907`, `session_start_nlv`, `daily_loss_limit_usd`). Do not overwrite later that day. If today’s record cannot be read or established: exits only
- Use Options Watchlist + all other watchlists; no crypto; no index
- PDT: do **not** reduce day-trade frequency (owner lock; owner stated PDT rule no longer exists — not independently verified here)
- Account: Agentic only
