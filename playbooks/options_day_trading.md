# Options Day Trading Playbook

**Status: RELEASED** (owner approved 2026-08-30)

Live `place_*` from **this Cursor chat (Agent F)** still requires an explicit confirm of a **specific** order.

Autonomous placing is a **separate** Cursor Automation (Agent H). Paste `playbooks/agent_h_autonomous.PROMPT.md` at https://cursor.com/automations and activate it to turn H ON. Disable that Automation to turn H OFF. That prompt is the standing place-permission; this chat is not.

## Locked rules
- Long call or long put only (no shorts)
- Expiry ≤ 7 DTE
- Strike: ATM preferred, else 1 OTM
- Delta band preference: abs(delta) 0.40–0.50 from Robinhood quotes only
- Max 1 contract
- Liquidity: bid–ask under **5–10% of the option’s price** (prefer ≤ 5%; reject > 10%). No absolute-dollar override. Reject one-sided quotes
- Exits: stop loss **20–50%** of premium; profit target **30–100%+** of premium; aim **1:2 risk-to-reward** (reward ≥ 2× risk). Owner-locked working pair: **−20% / +40%**. Broker **stop first** until OCO exists
- No new options entries overnight
- Index options allowed
- Use Options Watchlist + all other watchlists; no crypto
- PDT: do **not** reduce day-trade frequency (owner lock: accept risk; owner stated PDT rule no longer exists — not independently verified here)
- Account: Agentic only
