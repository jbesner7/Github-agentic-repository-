# RTH-only lock

Do **not** paste this file into an Automation.

Canonical prompt: `playbooks/agent_h_autonomous.PROMPT.md`.
Canonical rules: `config/rules.json` → `agent_h` (`schema_version` 2026-09-06.2). Git lease on `origin/main` is H’s concurrency gate.

RTH = Mon–Fri 09:30 inclusive–16:00 exclusive, `America/New_York`.
No extended, overnight, or weekend **scan or buy**.
Agent H and F options: no new option entry before 09:45 ET. Practical H 10m+retest window is about 13:10–15:45 ET. Recalculate current DTE every run. Expiration day: begin 15:30 ET, absolute 15:45 ET. DTE 1–3: begin 15:40 ET, flat by 15:45 ET. Leftover 4–7 DTE while overnight is off: treat as 1–3 (begin 15:40).
Overnight holding is **disabled**. This connection supports GFD option stop-market only; do not attempt GTC. Flatten every open option by 15:45 ET. Equities flatten before 16:00 ET (F only; H has no equity fallback).
Agent H charts: daily → 1-hour → completed 10-minute → live quote. Daily neckline governs the 10m breakout. No 1m / 3m / 5m.
