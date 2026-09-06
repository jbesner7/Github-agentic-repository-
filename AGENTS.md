# Agent operating notes

This repo is a gated Robinhood pipeline for **Agentic ••••2907** only. Mask accounts as ••••2907 / ••••5638. Pass the full account number only in RH tool args.

## Roles

- **F (this chat):** supervised. `place_*` only after an explicit confirm of a **specific** order. If H is enabled, do not place during RTH. Re-quote live. Never place from `signals/*`. F may still use the equities playbook after a specific confirm. `pipeline/execution.py` enforces confirm, playbook release, RTH, the **15:45** ceiling, **09:45** for options, and H-owns-RTH. Fee, signed-delta, quote-freshness, BOD NLV, pagination, and cancel-confirm are **live F obligations** on the same numbers as H — they are not automated in `can_place_live`.
- **H (Automation):** unsupervised. Canonical prompt: `playbooks/agent_h_autonomous.PROMPT.md` (`schema_version` **2026-09-06.5**). Re-paste after every prompt change. One Automation only (`9af478e7-a454-11f1-a7d1-d6b4613131ce`). **Options only** — no equity fallback. Cursor may start overlapping runs; **Git lease on `origin/main` is the concurrency gate for new entries.** Emergency protection does not wait on Git. Do not assume a scheduler concurrency setting exists.

## Source of truth

- Trading numbers: `config/rules.json` → `agent_h` only. This prompt/chat defines workflow and prohibitions. Never choose precedence by filesystem timestamps. If a required value is missing or conflicts with a hard prohibition, place nothing.
- Kill switch + tool allowlist only: `config/autonomous_permissions.json` (must exist and `status` = `ACTIVE` for new entries; inactive status still allows cancel / protect / reduce / close of existing exposure unless the owner says stop all order activity, including exits)
- Options: `playbooks/options_day_trading.md` (RELEASED)
- Equities: `playbooks/equities_day_trading.md` (RELEASED)
- Do not paste `playbooks/rth_only.PROMPT.md`

## Session

RTH = Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`. No extended/overnight/weekend **scan or buy**. Equities flatten before close (F only).

Agent H and F option entries: never before **09:45 ET**. Practical H 10m+retest window is about **13:10–15:45 ET**. Equity day trades (F only) may start at 09:30 if H is disabled. Monitor from 09:30. Hard DTE range **2–7** (no 0–1 DTE; owner-only re-enable on `main`). While overnight is disabled, H evaluates existing expirations in this order: **4, 5, 6, 7, 3, 2 DTE**, and flattens the same day regardless of entry DTE. Recalculate **current DTE** every run. Expiration day: begin flatten **15:30**, absolute **15:45**. DTE 1–3: begin flatten **15:40**, flat by **15:45**. Overnight holding is **off**. This connection supports GFD option `stop_market` only — do not attempt GTC. The stop is not guaranteed risk.

Prefer a broker **beginning-of-day NLV**. Midday first-fire equity is `first_fire_baseline_nlv` only and cannot authorize a new H entry. If genuine BOD NLV cannot be established: exits/protection only.

H graphs on the underlying, in this order only: **daily setup → 1-hour confirmation → completed 10-minute trigger → live quote → option review**. Daily neckline governs the 10m breakout. Do not use 1m or 3m (noise) or 5m (unnecessary; makes stateless runs inconsistent). No index options at launch.

## Lease and orders

H lease: `journal/h_lease.json`. Acquire it **after** the clock / `main` checkout / lock-file / RTH gates and **before** account, scan, or review. After acquire: select ••••2907, confirm core recovery tools, read `rules.json` / permissions / playbook, then reconstruct exposure and working orders from the broker before scan, BOD, session counters, or new-entry capability checks. Schema or `rules_prompt_mismatch` means place nothing, including leftover protection. Renew before a new entry unless at least **6 minutes** remain. Immediately before every `main` journal or lease commit, `git fetch origin` and `git pull --ff-only origin main` (or rebase a local unpushed commit onto `origin/main`), then **re-read** `origin/main:journal/h_lease.json` before writing. A pull that brought in **another** run’s lease is held — do not overwrite it. This run’s own working-tree lease write after a rebase does **not** block a retry; only the remote file decides whether the lease is free. Never force-push. A rejected acquire is retried once after rebase only if the **remote** lease is still free. The lease is not acquired unless the commit successfully pushes to `origin/main`. Then immediately `git fetch origin` and read the file from `origin/main`. The remote lease must contain this run’s exact `automation_id`, `run_id`, `started_et`, and `expires_et`. Re-fetch and verify immediately before every **new-entry** `place_option_order`. Emergency protection does not require Git. A rejected or conflicting acquire means place nothing new and exit unless Git is down and leftover exposure needs emergency protection. A failed acquire must not clear or modify the lease. Only the matching `run_id` may renew or release it. TTL is 12 minutes; renew before fewer than 3 minutes remain. If Git is reachable and this run already filled and the lease later expires: reacquire through commit/push/fetch/verify before any recovery ticket. Never place from a one-moment observation that no other unexpired lease existed. If another run holds it: journal `lease_held_after_fill`, place nothing. The new owner inspects exposure first. Each fire is stateless; reconstruct management from broker positions and working orders. Locked numbers are the `INV[key]=value` registry in the H prompt / `pipeline/h_invariants.py`.

After every cancel: poll to a terminal state, reconcile cumulative filled quantity, protect every fill. Never place a replacement unless zero fill and cancellation are confirmed. Never rest a full-quantity TP or liquidation against a working full-quantity stop.

Protective stop: `type=stop_market`, `time_in_force=gfd`, `position_effect=close`, `side=sell`, `quantity=filled_quantity`. Trigger = 80% of fill **rounded toward the fill on parsed `min_ticks`**, and the rounded trigger must stay below the live option bid. Never infer a tick from the premium. Verify accepted+GFD. Do not attempt GTC. From 09:30–09:44:59, do not place a new option stop-market; if a stop is missing, sell-to-close at the live bid. Entry replacement is +1 tick only when that price is still ≤ live ask and ≤ the tick-floored independent `max_acceptable_debit` cap. Mandatory liquidation repeats every 15s until flat; the one-replace limit does not apply. Forced liquidation does not restore the stop.

H fee gate (every trade): `planned_loss ≤ 0.49%` of current NLV **and** `planned_loss + estimated_round_trip_fees ≤ 0.50%` of current NLV. Prefer a valid **positive** `total_fee`. If `total_fee` is `$0.00` and any component is `> 0`, journal `fee_conflict`, do not trust the zero total, do not estimate, and treat fees as $0 in the 0.50% sum.

Call delta **+0.40 through +0.50**. Put delta **−0.50 through −0.40**. Do not use absolute-only delta. ATM = nearest strike; call/put ties use lower/higher strike; OTM is exactly one listed strike beyond ATM after strikes bracket spot.

Underlying live quote: regular session, ≤5 seconds old, positive bid/ask, bid ≤ ask. Call trigger = live ask. Put trigger = live bid. Do not describe last or midpoint as executable. Recheck before option review.

Robinhood MCP has no `open=true` order filter. Working option states: `queued`, `confirmed`, `partially_filled`, `pending_cancelled`. Working equity states: `new`, `queued`, `confirmed`, `unconfirmed`, `partially_filled`. Exhaust pagination before concluding that no working order, earlier entry, stop-out, strike bracket, or duplicate account exists.

If a required RH tool or field is missing (`get_realized_pnl`, earnings tools, news, and the rest of `agent_h.required_tools`), fail closed. Do not improvise.

## Journal

Append `journal/YYYY-MM-DD.md` on **`main`** only. `git checkout main && git pull origin main` before reads or writes. Do not open a new PR. Do not call `open_git_pr`. Do not commit `MEMORIES.md`.

## Honesty

Never invent Greeks or prices. Never mention internal account-permission fields in user-facing text. Resolve the tradable account by nickname Agentic and last-4 **2907**.
