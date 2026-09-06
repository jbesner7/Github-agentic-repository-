# Agent operating notes

This repo is a gated Robinhood pipeline for **Agentic ••••2907** only. Mask accounts as ••••2907 / ••••5638. Pass the full account number only in RH tool args.

## Roles

- **F (this chat):** supervised. `place_*` only after an explicit confirm of a **specific** order. If H is enabled, do not place during RTH. Re-quote live. Never place from `signals/*`. F may still use the equities playbook after a specific confirm. `pipeline/execution.py` enforces confirm, playbook release, RTH, the **15:45** ceiling, **09:45** for options, and H-owns-RTH. Fee, signed-delta, quote-freshness, BOD NLV, pagination, and cancel-confirm are **live F obligations** on the same numbers as H — they are not automated in `can_place_live`.
- **H (Automation):** unsupervised. Paste file: `playbooks/agent_h_autonomous.PROMPT.md` (`schema_version` **2026-09-06.9**). Follow the numbered card at the top of that file. Copy from `BEGIN AGENT H PROMPT` through the end into Agentic AI Bot. Re-paste after every prompt change. One Automation only (`9af478e7-a454-11f1-a7d1-d6b4613131ce`). **Options only.**

## Source of truth

- Trading numbers: `config/rules.json` → `agent_h` only. Never choose precedence by filesystem timestamps. If a required value is missing or conflicts with a hard prohibition, place nothing.
- Kill switch / tool allowlist: `config/autonomous_permissions.json` (`ACTIVE` for new entries; inactive still allows cancel / protect / reduce / close unless the owner says **stop all order activity, including exits**)
- Options: `playbooks/options_day_trading.md`. Equities (F only): `playbooks/equities_day_trading.md`.
- Do not paste `playbooks/rth_only.PROMPT.md`

## Session (F)

RTH = Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`. No extended/overnight/weekend **scan or buy**. Equities flatten before close (F only). Option entries never before **09:45 ET**. Overnight holding is **off**. GFD option `stop_market` only — do not attempt GTC.

H charts, DTE ranking, and liquidation clocks: follow the H prompt. When F places after a specific confirm, use the same live quote, fee, and cancel-confirm rules as `rules.json` → `agent_h`.

## F place obligations

After every cancel: poll to a terminal state, reconcile cumulative filled quantity, protect every fill. Never place a replacement unless zero fill and cancellation are confirmed. Never rest a full-quantity TP or liquidation against a working full-quantity stop.

Protective stop, fee ceilings, signed delta, and underlying-quote rules: same numbers as `agent_h`. Exhaust pagination before concluding no working order, earlier entry, stop-out, strike bracket, or duplicate account. If a required RH tool or field is missing, fail closed. Do not improvise.

## Journal

Append `journal/YYYY-MM-DD.md` on **`main`** only. `git checkout main && git pull origin main` before reads or writes. Do not open a new PR. Do not call `open_git_pr`. Do not commit `MEMORIES.md`.

## Cost

H 15-minute cadence is leftover coverage. Outside RTH is clock-only. F does not run H’s watchlist, historicals, or option-chain waterfall. Re-quote immediately before review and before place. Stop paging after a positive match except to prove there is one ••••2907 account. A rate-limited tool blocks a new entry.

## Honesty

Never invent Greeks or prices. Never mention internal account-permission fields in user-facing text. Resolve the tradable account by nickname Agentic and last-4 **2907**.
