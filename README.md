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

- Options first, then long-share equity day trade. **No crypto. No shorting. No inverse ETFs.**
- Max **one** open position. Options size **1** contract. Equities: whole shares up to buying power.
- Options: long call / long put, DTE 0–7, ATM else one OTM, abs(delta) 0.40–0.50 from RH quotes only. SL **−20%** / TP **+40%** of premium. May **hold overnight** with the broker stop. No new option entries overnight or after 15:45 ET.
- Equities: long shares only. SL **−20%** / TP **+25%** of cost. **Flatten before 16:00 ET.** No new entries after 15:45 ET.
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

## Printable Python source (F + H)

All Python used by this chat (Agent F) and the autonomous bot (Agent H), organized by module:

- Print: [`docs/agentic-python-source-printable.html`](docs/agentic-python-source-printable.html) (Print / Save as PDF)
- Python file: [`docs/agentic_python_source_book.py`](docs/agentic_python_source_book.py)
- PDF: [`docs/agentic-python-source.pdf`](docs/agentic-python-source.pdf)

```bash
python3 scripts/build_python_source_book.py
```


## Kill switch

Disable Agentic AI Bot, or delete `config/autonomous_permissions.json`.

