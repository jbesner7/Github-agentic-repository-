# Agent operating notes

This repo is a gated Robinhood pipeline for **Agentic ••••2907** only. Mask accounts as ••••2907 / ••••5638. Pass the full account number only in RH tool args.

## Roles

- **F (this chat):** supervised. `place_*` only after an explicit confirm of a **specific** order. If H is enabled, do not place during RTH. Re-quote live. Never place from `signals/*`.
- **H (Automation):** unsupervised. Canonical prompt: `playbooks/agent_h_autonomous.PROMPT.md`. Re-paste after every prompt change. One Automation only.

## Source of truth

- Trading numbers and session: `config/rules.json`
- Kill switch + tool allowlist only: `config/autonomous_permissions.json` (must exist and `status` = `ACTIVE`)
- Options: `playbooks/options_day_trading.md` (RELEASED)
- Equities: `playbooks/equities_day_trading.md` (RELEASED)
- Do not paste `playbooks/rth_only.PROMPT.md`

## Session

RTH = Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`. No extended/overnight/weekend **scan or buy**. Equities flatten before close. Options may hold overnight with the broker stop.

Robinhood MCP 1-minute bar is `interval=minute` (not `1minute`). 5-minute is `5minute`. There is **no** `3minute` (aggregate from `minute` via `pipeline.bars`) and **no** `15minute`. No `open=true` order filter. Working option states: `queued`, `confirmed`, `partially_filled`, `pending_cancelled`. Working equity states: `new`, `queued`, `confirmed`, `unconfirmed`, `partially_filled`.

## Journal

Append `journal/YYYY-MM-DD.md` on **`main`** only. `git checkout main && git pull origin main` before reads or writes. Do not open a new PR. Do not call `open_git_pr`. Do not commit `MEMORIES.md`.

## Honesty

Never invent Greeks or prices. Never mention internal account-permission fields in user-facing text. Resolve the tradable account by nickname Agentic and last-4 **2907**.
