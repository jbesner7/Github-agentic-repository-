# Agentic trading repository

Robinhood automation for **one** account: Agentic **••••2907**. Never trade ••••5638.

Canonical machine spec: [`config/rules.json`](config/rules.json).  
Kill switch / tool allowlist: [`config/autonomous_permissions.json`](config/autonomous_permissions.json).  
Operator notes for agents: [`AGENTS.md`](AGENTS.md).

## Who places

| Who | When it may `place_*` |
|---|---|
| **Agent F** (this Cursor chat) | Only after an explicit confirm of a **specific** order. Blocked during RTH while H is enabled. Never from stale `signals/*`. |
| **Agent H** (Cursor Automation [Agentic AI Bot](https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce)) | Standing prompt is the permission. Disable the Automation (or delete the permissions file) to stop. |

Do not run two place-capable Automations. Git updates do **not** change the pasted Automation prompt — re-paste [`playbooks/agent_h_autonomous.PROMPT.md`](playbooks/agent_h_autonomous.PROMPT.md) after prompt edits.

## Locked rules (summary)

- **H is options only** (long call / long put). No equity fallback, no shares, no index options, no inverse ETFs, no crypto, no shorting. F may still use the equities playbook after a specific confirm when H does not own RTH.
- Max **one** open position. Options size **1** contract. Equities (F only): whole shares up to buying power.
- Options: hard DTE **2–7** (no 0–1 DTE). While overnight is **off**, H evaluates **2–3 DTE only**. ATM else one listed OTM. Signed delta: call **+0.40–+0.50**, put **−0.50–−0.40**. SL **−20%** / TP **+40%** of premium. Dual fee ceiling: planned loss ≤ 0.49% NLV **and** planned loss + fees ≤ 0.50% NLV.
- Overnight holding is **off** until a live GTC option stop is accepted and verified (this MCP documents `stop_market` as GFD-only). Flatten open options by **15:45 ET**.
- No new option entry before **09:45 ET** or after **15:45 ET**. Practical H window is about **13:10–15:45 ET**.
- Equities (F only): long shares only. SL **−20%** / TP **+25%** of cost. **Flatten before 16:00 ET.** No new equity entries after 15:45 ET.
- Scan and buy **RTH only** (Mon–Fri 09:30–16:00 ET). Intraday bars: `10minute` (Robinhood MCP has no `15minute`).
- After a fill: broker **STOP only**. No OCO. TP is watched on later RTH runs.

## H schedule

Schedule the Automation every **15 minutes** if you want. Each fire **exits before any market work** if it is not RTH. Skip journals **append on `main`** — do not open a new PR per skip. H must `checkout` + `pull` `main` before reading lock files.

## Read-only pipeline

```bash
python3 scripts/run_phase2_cycle.py
python3 -m pytest pipeline/tests -q
```

`signals/*` files in git are **historical snapshots**. Do not place from them.

## Kill switch

Disable Agentic AI Bot, or delete `config/autonomous_permissions.json`.
