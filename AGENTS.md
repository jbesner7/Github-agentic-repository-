# Agent operating notes

Account: Agentic **••••2907** only. Mask ••••2907 / ••••5638. Full number only in RH tool args.

## F dispatch (`pipeline/f_attention.py`)

This chat is supervised. Place only after an explicit confirm of a **specific** order.
If H is enabled during RTH: **place nothing**.
Do not run H’s waterfall, lease acquire, watchlists, historicals, or option-chain scan.
Locks: `pipeline/execution.py`, `config/rules.json` → `agent_h`.
Re-quote live. Never place from `signals/*`. Equities playbook only after a specific confirm.
After every cancel: poll to a terminal state, reconcile fills, protect every fill. Never rest a full-quantity TP or liquidation against a working full-quantity stop.

## H paste

`playbooks/agent_h_autonomous.PROMPT.md` (`schema_version` **2026-09-06.10**). Copy `BEGIN AGENT H PROMPT` through EOF into Agentic AI Bot (`9af478e7-a454-11f1-a7d1-d6b4613131ce`). Re-paste after every prompt change. Do not paste this file or `playbooks/rth_only.PROMPT.md`. After clock + exposure H runs `pipeline.h_dispatch.print_card` and executes only that card.

## Shared

Trading numbers: `config/rules.json` → `agent_h` only. Kill switch: `config/autonomous_permissions.json`. Options: `playbooks/options_day_trading.md`.
RTH = Mon–Fri 09:30–16:00 exclusive ET. Overnight **off**. GFD option `stop_market` only.
Journal on **`main`** only. Never force-push. Never invent Greeks or prices.
