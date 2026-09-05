# Options Day Trading Playbook

**Status: RELEASED** (owner approved 2026-08-30), with **2026-09-05 Agent H draft addenda** marked OWNER_DRAFT until the owner confirms them.

Live `place_*` from **this Cursor chat (Agent F)** still requires an explicit confirm of a **specific** order.

Autonomous placing is a **separate** Cursor Automation (Agent H). Owner activated **Agentic AI Bot** on 2026-08-30: https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce. Disable that Automation to turn H OFF. That prompt is the standing place-permission; this chat is not.

Agent H mandate: **long call or long put only.** No equity fallback.

## Locked rules

- Long call or long put only (no shorts)
- New entries: DTE **2–7** inclusive. **No 0 DTE. No 1 DTE** until separately validated by backtesting and paper trading and flipped in `config/rules.json` `agent_h.allow_0dte` / `allow_1dte`
- Strike: ATM preferred, else 1 OTM
- Delta band: abs(delta) 0.40–0.50 from Robinhood quotes only
- Max 1 contract
- Liquidity: valid bid and ask, **positive bid and ask sizes**, spread under **5–10% of the option’s price** (prefer ≤ 5%; reject > 10%). No absolute-dollar override. Reject missing Greeks, IV, open interest, volume, or quote timestamp
- **OWNER_DRAFT contract floors:** volume ≥ 100, open interest ≥ 200, quote `updated_at` within 15 seconds
- Exits: stop loss **20–50%** of premium; profit target **30–100%+** of premium; aim **1:2** risk-to-reward. Owner-locked working pair: **−20% / +40%**. Broker **stop first** until OCO exists
- Take-profit trigger is the live **bid** ≥ 140% of average fill premium (not mark, not last). Re-quote before review
- Session:
  - Monitor existing positions from **09:30 ET**
  - **No new option entry before 09:45:00 ET.** A new long option opens only when its protective stop can be accepted immediately
  - No new entries after **15:45 ET**
  - Any option **expiring today** must be sold to close by **15:30 ET**. Do not rely on automatic exercise
  - Open 2–7 DTE longs **may be held overnight** with the broker stop. **Owner confirmed 2026-08-31.** Do not flatten those at 16:00 ET
- Session caps (Agent H):
  - Maximum **two** new entries per trading day
  - Stop new entries after **two** losing trades
  - Maximum daily realized loss: **1% of NLV**
  - Minimum **30-minute** cooldown after an exit
  - Never re-enter the same underlying the same day after a stopped-out trade
- Cash caps (both must pass; skip if one contract fails either):
  - Maximum planned loss per trade: **0.5% of NLV**
  - Maximum option debit: **2.5% of NLV**
  - `required_cash = option_limit_price × 100` (limit, not midpoint)
  - **OWNER_DRAFT:** planned loss = debit × 20% stop
- Intraday graphs for H: live + **1-minute / 3-minute / 5-minute**. 3m is aggregated from 1m (`pipeline.bars.aggregate_to_minutes`). No `15minute`. No `10minute` as the primary H chart
- Daily direction must align with at least one of 1m / 3m / 5m. Require confirmed breakout + retest + underlying-price trigger. Pattern method is locked in the H prompt
- Earnings / news / corporate-action gate: no new short-DTE entries around earnings, halts, mergers, splits, or pending binary events unless explicitly permitted
- **OWNER_DRAFT IV:** reject missing IV; reject IV ≥ 150% or ≥ 1.25× ATM IV on the same expiry
- Entry: start at tick-rounded midpoint, never above ask, one replacement (+1 tick / 45s), cancel at 90s, re-quote before replace, never chase above the original max debit
- Partial fill: protect filled size immediately from broker average fill; cancel the remainder
- If fill succeeds and stop review/place fails: immediate controlled sell-to-close and journal `protection_failed`
- Re-read buying power immediately before place
- H lease: `journal/h_lease.json` + automation id `9af478e7-a454-11f1-a7d1-d6b4613131ce`
- Use Options Watchlist + all other watchlists; no crypto
- PDT: do **not** reduce day-trade frequency (owner lock; owner stated PDT rule no longer exists — not independently verified here)
- Account: Agentic only
