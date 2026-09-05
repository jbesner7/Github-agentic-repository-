# Agent operating notes

This repo is a gated Robinhood pipeline for **Agentic ••••2907** only. Mask accounts as ••••2907 / ••••5638. Pass the full account number only in RH tool args.

## Roles

- **F (this chat):** supervised. `place_*` only after an explicit confirm of a **specific** order. If H is enabled, do not place during RTH. Re-quote live. Never place from `signals/*`. F may still use the equities playbook after a specific confirm. Option tickets follow the same cancel-confirm, stop/TP conflict, pagination, signed-delta, dual fee, and quote-freshness rules as H.
- **H (Automation):** unsupervised. Canonical prompt: `playbooks/agent_h_autonomous.PROMPT.md` (`schema_version` **2026-09-05.2**). Re-paste after every prompt change. One Automation only (`9af478e7-a454-11f1-a7d1-d6b4613131ce`). **Options only** — no equity fallback. Set the Automation scheduler to **maximum concurrent runs = 1**.

## Source of truth

- Trading numbers: `config/rules.json` → `agent_h` only. This prompt/chat defines workflow and prohibitions. Never choose precedence by filesystem timestamps. If a required value is missing or conflicts with a hard prohibition, place nothing.
- Kill switch + tool allowlist only: `config/autonomous_permissions.json` (must exist and `status` = `ACTIVE`)
- Options: `playbooks/options_day_trading.md` (RELEASED)
- Equities: `playbooks/equities_day_trading.md` (RELEASED)
- Do not paste `playbooks/rth_only.PROMPT.md`

## Session

RTH = Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`. No extended/overnight/weekend **scan or buy**. Equities flatten before close (F only).

Agent H new entries: never before **09:45 ET**. Practical 10m+retest window is about **13:10–15:45 ET**. Monitor from 09:30. Hard DTE range **2–7** (no 0–1 DTE; owner-only re-enable on `main`). While overnight is disabled, H evaluates **2–3 DTE only**. Recalculate **current DTE** every run. Expiration day: begin flatten **15:30**, absolute **15:45**. DTE 1–3: begin flatten **15:40**, flat by **15:45**. Overnight holding is **off** until a live GTC option stop is accepted and verified — this MCP documents `stop_market` as GFD-only. The stop is not guaranteed risk.

Prefer a broker **beginning-of-day NLV**. Midday first-fire equity is `first_fire_baseline_nlv` only and cannot authorize a new H entry. If genuine BOD NLV cannot be established: exits/protection only.

H graphs on the underlying, in this order only: **daily setup → 1-hour confirmation → completed 10-minute trigger → live quote → option review**. Daily neckline governs the 10m breakout. Do not use 1m or 3m (noise) or 5m (unnecessary; makes stateless runs inconsistent). No index options at launch.

## Lease and orders

H lease: `journal/h_lease.json`. Valid only after a successful push to `origin/main`, then a fetch that confirms the remote file contains this run’s `run_id`. Recheck that remote lease immediately before every `place_option_order`. A failed lease push means place nothing and exit.

After every cancel: poll to a terminal state, reconcile cumulative filled quantity, protect every fill. Never place a replacement unless zero fill and cancellation are confirmed. Never rest a full-quantity TP or liquidation against a working full-quantity stop.

Protective stop attempt: `type=stop_market`, `time_in_force=gtc`, `position_effect=close`, `side=sell`, `quantity=filled_quantity`. Verify accepted+GTC. If GTC is unsupported, disable overnight. From 09:30–09:44:59, do not place a new option stop-market; if a stop is missing, sell-to-close at the live bid.

H fee gate (every trade): `planned_loss ≤ 0.49%` of current NLV **and** `planned_loss + estimated_round_trip_fees ≤ 0.50%` of current NLV. Prefer a valid **positive** `total_fee`. If `total_fee` is `$0.00` and any component is `> 0`, journal `fee_conflict`, do not trust the zero total, do not estimate, and treat fees as $0 in the 0.50% sum.

Call delta **+0.40 through +0.50**. Put delta **−0.50 through −0.40**. Do not use absolute-only delta. ATM = nearest strike; call/put ties use lower/higher strike; OTM is exactly one listed strike beyond ATM after strikes bracket spot.

Underlying live quote: regular session, ≤5 seconds old, positive bid/ask, bid ≤ ask; last if inside the market, else mid. Recheck before option review.

Robinhood MCP has no `open=true` order filter. Working option states: `queued`, `confirmed`, `partially_filled`, `pending_cancelled`. Working equity states: `new`, `queued`, `confirmed`, `unconfirmed`, `partially_filled`. Exhaust pagination before concluding that no working order, earlier entry, stop-out, strike bracket, or duplicate account exists.

If a required RH tool or field is missing (`get_realized_pnl`, earnings tools, news, and the rest of `agent_h.required_tools`), fail closed. Do not improvise.

## Journal

Append `journal/YYYY-MM-DD.md` on **`main`** only. `git checkout main && git pull origin main` before reads or writes. Do not open a new PR. Do not call `open_git_pr`. Do not commit `MEMORIES.md`.

## Honesty

Never invent Greeks or prices. Never mention internal account-permission fields in user-facing text. Resolve the tradable account by nickname Agentic and last-4 **2907**.
