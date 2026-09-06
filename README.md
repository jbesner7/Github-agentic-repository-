# Agentic trading repository

Robinhood automation for **one** account: Agentic **••••2907**. Never trade ••••5638.

Canonical machine spec: [`config/rules.json`](config/rules.json).  
Kill switch / tool allowlist: [`config/autonomous_permissions.json`](config/autonomous_permissions.json).  
Operator notes for agents: [`AGENTS.md`](AGENTS.md).

## Who places

| Who | When it may `place_*` |
|---|---|
| **Agent F** (this Cursor chat) | Only after an explicit confirm of a **specific** order. Blocked during RTH while H is enabled. Never from stale `signals/*`. |
| **Agent H** (Cursor Automation [Agentic AI Bot](https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce)) | Standing prompt is the permission. Disable the Automation to stop new entries. Deleting the permissions file also blocks new entries; leftover exposure may still be flattened unless the owner says stop all order activity, including exits. |

Do not run two place-capable Automations. Git updates do **not** change the stored Automation prompt. Paste instructions: [`playbooks/agent_h_autonomous.PROMPT.md`](playbooks/agent_h_autonomous.PROMPT.md) — copy from `BEGIN AGENT H PROMPT` through the end into [Agentic AI Bot](https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce). Re-paste after every prompt change.

## Locked rules (summary)

- **H is options only** (long call / long put). No equity fallback, no shares, no index options, no inverse ETFs, no crypto, no shorting. F may still use the equities playbook after a specific confirm when H does not own RTH.
- Max **one** open position. Options size **1** contract. Equities (F only): whole shares up to buying power.
- Options: hard DTE **2–7** (no 0–1 DTE). While overnight is **off**, H evaluates **4, 5, 6, 7, 3, 2 DTE** in that order and flattens the same day. ATM else one listed OTM (not after a broker `order_checks` block). Signed delta: call **+0.40–+0.50**, put **−0.50–−0.40**. SL **−20%** / TP **+40%** of premium. Dual fee ceiling: planned loss ≤ 0.49% NLV **and** planned loss + fees ≤ 0.50% NLV.
- Overnight holding is **off**. This connection supports GFD option `stop_market` only; do not attempt GTC. Flatten open options by **15:45 ET**.
- No new option entry before **09:45 ET** or after **15:45 ET**. Practical H window is about **13:10–15:45 ET**.
- Equities (F only): long shares only. SL **−20%** / TP **+25%** of cost. **Flatten before 16:00 ET.** No new equity entries after 15:45 ET.
- Scan and buy **RTH only** (Mon–Fri 09:30–16:00 ET). Intraday bars: `10minute` (Robinhood MCP has no `15minute`).
- After a fill: broker **STOP only**. No OCO. TP is watched on later RTH runs.

## H schedule

Schedule the Automation every **15 minutes** if you want. Each fire **exits before any market work** if it is not RTH. Skip journals **append on `main`** — do not open a new PR per skip. H must `checkout` + `pull` `main` before reading lock files. Cursor may start overlapping H runs; **`journal/h_lease.json` on `origin/main` is the concurrency gate for new entries.** Emergency protection does not wait on Git. Duplicate leftover closes are blocked by broker occupancy and a deterministic `ref_id`, not by the lease. Outside RTH is clock-only. Full scan runs only 13:10–15:45 when flat. Never force-push. Schema **2026-09-06.10**. After clock + exposure H runs `pipeline.h_dispatch.print_card` and executes only that card.

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

The book is a **frozen snapshot of schema `2026-09-06.1`**. Live Agent H on `main` is schema **`2026-09-06.8`**. Do **not** paste this book, or any file under `docs/`, into the Automation. H’s live permission is the pasted prompt from [`playbooks/agent_h_autonomous.PROMPT.md`](playbooks/agent_h_autonomous.PROMPT.md) on `main` (copy `BEGIN AGENT H PROMPT` through EOF). Do not rebuild the book unless the owner asks. H charts are daily → hour → 10-minute → live quote only.

## Kill switch

Disable Agentic AI Bot to stop new unsupervised entries. Deleting `config/autonomous_permissions.json` (or setting `status` not `ACTIVE`) blocks new entries only; existing exposure may still be cancelled, protected, reduced, or closed unless the owner says **stop all order activity, including exits**.
