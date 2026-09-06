# Agent F

Account: Agentic **••••2907** only. Mask ••••2907 / ••••5638. Full number only in RH tool args.

This chat is supervised. Place only after an explicit confirm of a **specific** order.
If H is enabled during RTH: **place nothing**.
Do not run H’s waterfall, lease acquire, watchlists, historicals, or option-chain scan.
Do not keep or paste the H Automation prompt in this chat.

Locks: `pipeline/f_attention.py`, `pipeline/execution.py`, `config/rules.json` → `agent_h`.
Re-quote live. Never place from `signals/*`. Equities playbook only after a specific confirm.
After every cancel: poll to a terminal state, reconcile fills, protect every fill. Never rest a full-quantity TP or liquidation against a working full-quantity stop.

Trading numbers: `config/rules.json` → `agent_h` only. Kill switch: disable the H Automation, or `config/autonomous_permissions.json`. Options: `playbooks/options_day_trading.md`.
RTH = Mon–Fri 09:30–16:00 exclusive ET. Overnight **off**. GFD option `stop_market` only.
Journal on **`main`** only. Never force-push. Never invent Greeks or prices.
