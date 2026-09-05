# Agent operating notes

This repo is a gated Robinhood pipeline for **Agentic ••••2907** only. Mask accounts as ••••2907 / ••••5638. Pass the full account number only in RH tool args.

## Roles

- **F (this chat):** supervised. `place_*` only after an explicit confirm of a **specific** order. If H is enabled, do not place during RTH. Re-quote live. Never place from `signals/*`. F may still use the equities playbook after a specific confirm.
- **H (Automation):** unsupervised. Canonical prompt: `playbooks/agent_h_autonomous.PROMPT.md`. Re-paste after every prompt change. One Automation only (`9af478e7-a454-11f1-a7d1-d6b4613131ce`). **Options only** — no equity fallback. Lease: `journal/h_lease.json`.

## Source of truth

- Trading numbers and session: `config/rules.json`
- Kill switch + tool allowlist only: `config/autonomous_permissions.json` (must exist and `status` = `ACTIVE`)
- Options: `playbooks/options_day_trading.md` (RELEASED)
- Equities: `playbooks/equities_day_trading.md` (RELEASED)
- Do not paste `playbooks/rth_only.PROMPT.md`

## Session

RTH = Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`. No extended/overnight/weekend **scan or buy**. Equities flatten before close (F only).

Agent H new entries: **09:45–15:45 ET** only. Monitor from 09:30. New entries **2–7 DTE** (no 0–1 DTE; owner-only re-enable on `main`). Recalculate **current DTE** every run. Expiration day: target **15:30**, absolute **15:45**. Current DTE **≤ 3** flatten by **15:45 ET**. Current DTE **≥ 4** may hold overnight with the broker stop, never through earnings/binary events. The stop is not guaranteed risk. Session-start NLV lives in `journal/h_session.json`.

H graphs: **daily + 1-hour + 10-minute** only. Do not use 1m/3m/5m for Agent H. No index options at launch.

Robinhood MCP has no `open=true` order filter. Working option states: `queued`, `confirmed`, `partially_filled`, `pending_cancelled`. Working equity states: `new`, `queued`, `confirmed`, `unconfirmed`, `partially_filled`.

## Journal

Append `journal/YYYY-MM-DD.md` on **`main`** only. `git checkout main && git pull origin main` before reads or writes. Do not open a new PR. Do not call `open_git_pr`. Do not commit `MEMORIES.md`.

## Honesty

Never invent Greeks or prices. Never mention internal account-permission fields in user-facing text. Resolve the tradable account by nickname Agentic and last-4 **2907**.
