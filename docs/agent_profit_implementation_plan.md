# AGENT PROFIT IMPLEMENTATION PLAN

**Status:** audit + plan only. **Do not implement until the owner approves this document.**

**Date:** 2026-10-06  
**Account:** Agentic ••••2907 only. Never ••••5638.  
**This PR does:** add this plan.  
**This PR does not:** create an `agent_profit/` package, change Agent H, edit `config/rules.json`, edit `config/autonomous_permissions.json`, authenticate Robinhood MCP, or place any order.

Agent Profit is a **new, isolated, long-only U.S. stock bot**. It must coexist with Agent H. It must not replace, convert, or merge with H.

---

## Owner decisions required before any build

These are not implementation details. Building without them will either violate the Profit spec or silently break H.

1. **Second place-capable Automation.** `README.md` currently says: do not run two place-capable Automations. Agent Profit, if autonomous, needs its own Cursor Automation (or another runtime). That is an explicit exception to the current lock. Approve the exception, or Profit stays a dry helper that Agent F still cannot place from without a specific-order confirm.

2. **Shared-account occupancy.** H’s locked rule is `block_new_entry_if_any_equity_option_or_working_order: true`. If Profit holds even one stock or has a working equity ticket, **H will refuse new option entries**. This plan does **not** change that H rule. Owner choices:
   - Accept that H stays flat / manage-only while Profit has stock.
   - Later approve a **separate** H occupancy change (out of scope here).
   - Use a different account for Profit (not requested; not assumed).

3. **Robinhood session windows, not the 04:00 assumption.** Official Robinhood extended hours are **07:00–09:30 ET** and **16:00–20:00 ET**. Fractional extended-hours trading ends **19:30 ET**. The 24 Hour Market is **select names, whole-share limit orders only**, roughly Sun 20:00–Fri 20:00 ET. Profit must not invent a 04:00 premarket window. If a name is not 24h-eligible, do not trade it overnight.

4. **Honor-system Python vs hard interceptor.** Same as H: a Cursor Automation can call `place_equity_order` without importing Python. Profit’s risk engine can be deterministic in-repo, but MCP placement is still LLM-mediated unless a later runtime wraps the tools. This plan uses H’s pattern: Python prints a PASS/REJECT card; the Automation may place **only** that card; tests lock the card. It does not claim Python can intercept MCP.

5. **Trade Approvals.** Official Robinhood: Trade Approvals default **off** for external MCP. If the owner turns them on, Profit cannot autonomously place. Confirm they stay off for MCP if autonomous execution is required.

Until those are answered, the correct next step is approval of this plan — not code.

---

## 1. Current Agent F architecture

Agent F is **this supervised Cursor chat**, not a bot.

| Piece | Role |
|---|---|
| `AGENTS.md` | Chat lock: specific-order confirm; if H is enabled during RTH, F places nothing; do not run H’s waterfall; do not paste the H prompt |
| `pipeline/f_attention.py` | `f_may_place` / `f_may_run_h_scan() == False` |
| `pipeline/execution.py` | Dry `can_place_live` + review/place **payload builders**. Does not call the broker |
| `playbooks/equities_day_trading.md` | F-only equity path |
| `config/rules.json` → `execution.agent_f` | Confirm required; H owns RTH while enabled; never place from `signals/*` |

F may propose long shares after a **specific** confirm, only when H does not own RTH. F is not Agent Profit and must not become the Profit runtime.

## 2. Current Agent H architecture

Agent H is the existing **unsupervised options Automation**.

| Piece | Role |
|---|---|
| Cursor Automation `9af478e7-a454-11f1-a7d1-d6b4613131ce` | “Agentic AI Bot”. Standing place permission |
| `playbooks/agent_h_autonomous.PROMPT.md` | Live permission text. Git updates do not change the stored prompt |
| `config/rules.json` → `agent_h` | Schema **2026-09-08.1**. Trading numbers live here only |
| `config/autonomous_permissions.json` | Kill switch + option-only place allowlist |
| `pipeline/h_*.py` | Honor-system helpers (dispatch, gates, budget, continuity, closer, attention, failures, invariants). H cannot import them at Automation runtime |
| `journal/h_lease.json` on `origin/main` | Concurrency gate for new H entries |

H mandate: **long call or long put only**. No equity fallback. No shares. No index options. No inverse ETFs. No crypto. No shorting. Overnight **off**. Flatten options by 15:45 ET. Practical scan **13:10–15:45 ET** when flat. Max one H position, 1 contract, −20% / +40%, 2.5% debit / 0.49% planned-loss / 1% daily realized-loss of BOD NLV.

H occupancy is **account-wide**: any equity, option, or working order blocks a new H entry. H leftover/manage helpers are option-oriented (`has_option_position`). H is already forbidden from `place_equity_order` / `cancel_equity_order`.

## 3. Existing Robinhood / MCP integration

There is **no** custom Robinhood SDK, scraper, or in-repo MCP client.

- Brokerage is the **official Robinhood Trading MCP** (Cursor-hosted).
- This environment’s RH MCP namespace is **`needsAuth`**. This audit did **not** call `mcp_auth` and did not list live tool schemas.
- Official external-agent equity tools (Robinhood “Trading with your agent”, 2026-10-06 fetch): `get_equity_positions`, `get_equity_tax_lots`, `get_equity_quotes`, `get_equity_orders`, `get_equity_tradability`, `review_equity_order`, `place_equity_order`, `cancel_equity_order`.
- Official supporting reads: `get_accounts`, `get_portfolio`, `get_realized_pnl`, `get_pnl_trade_history`, `search`, watchlists, `get_equity_historicals`, `get_equity_fundamentals`, `get_financials`, `get_equity_price_book`, `get_equity_technical_indicators`, `get_earnings_results`, `get_earnings_calendar`, `get_equity_news`, SEC filing tools, `get_equity_analyst_ratings`, scanners (`get_scans`, `run_scan`, …).
- **Not** on the official external-agent table: `get_market_hours`. Treat holiday / special-session detection as **UNKNOWN** until a verified tool or calendar source exists. Fail closed; do not invent hours.
- Official copy: agents may place **long** equities, options, and crypto. Shorting is not part of the official agent-trading sentence. Do not use `sell_short` even if a community schema mentions it.
- Community / unofficial docs mention `market_hours` values `regular_hours`, `extended_hours`, `all_day_hours`. **UNKNOWN until live `place_equity_order` / `review_equity_order` schema is read after owner-approved auth.** Do not hard-code unofficial parameter names into production validators until verified.
- Advanced-order tools exist on the official page (`get_advanced_orders`, `place_advanced_order`, …). H already notes this connection has no usable `get_advanced_orders` for its option path. Profit must not assume OCO exists.
- Trade Approvals: off by default for external MCP; if on, autonomous place is blocked.

## 4. Existing market-data infrastructure

| Module | What it does | Profit fit |
|---|---|---|
| `pipeline/quotes.py` | Executable underlying bid/ask, 5s age, BOD NLV field candidates | Reuse **parsers**, not H’s regular-session-only policy |
| `pipeline/equity_day_trade.py` | Bid/ask check, RTH-only tradability, **whole-share** sizer, inverse-ETF denylist | **Do not reuse** sizing, RTH-only buy, or “long ETF OK” policy |
| `pipeline/universe.py` | Watchlist union; skips crypto/index; treats unnamed instruments as equity/**ETF** | Reuse crypto/index skip; **add** a stock-only classifier |
| `pipeline/patterns.py` | Locked H pattern types / waterfall | Knowledge only. Profit must not inherit H’s 13:10 window or forbidden 5-minute charts as a hard ban if Profit’s own scan uses 5-minute **scheduling** |
| `pipeline/news.py` | Packages RH news/earnings; invents no sentiment | Reuse as a catalyst packager |
| `pipeline/session.py` | Clock-only Mon–Fri 09:30–16:00 ET. **No holidays, no early close, no extended hours** | **Do not reuse** as Profit’s session engine |

Robinhood MCP has no `15minute` interval. Intraday bars that exist: `10minute`, `hour`, `day` (and others H forbids for itself). Profit may use broker-supported intervals for **its** analysis; it must not change H’s forbidden-timeframe lock.

## 5. Existing playbooks

| Playbook | Owner | Profit use |
|---|---|---|
| `playbooks/options_day_trading.md` | H | Knowledge only. **Never** permission to trade options |
| `playbooks/equities_day_trading.md` | F | **Conflicts** with Profit (see below). Knowledge only; do not import its numbers |
| `playbooks/chart_patterns.md` | Signal heuristics | Knowledge only |
| `playbooks/agent_h_autonomous.PROMPT.md` | H Automation | **Do not paste. Do not edit for Profit.** |
| `playbooks/rth_only.PROMPT.md` | Session reminder | Conflicts with Profit’s extended/24h mandate |

F equity playbook locks that **must not** become Profit defaults:

- Whole shares only; no `$` / fractional tickets
- RTH only; flatten before 16:00 ET
- −20% stop / +25% target
- Size up to **full buying power**
- Max **one** open position account-wide
- Long index ETFs (SPY / VTI / QQQ) allowed
- ADV ≥ 2,000,000

Profit’s authority is different: fractional OK if the broker supports it; $50 cap; 5 positions; $50 daily loss; 50% stop; +10% target; no ETFs; session = whatever the broker and **that** security actually support.

## 6. Existing autonomous scheduler

There is **no Python daemon**.

- H is a Cursor Automation. Owner-side cadence is **15 minutes**.
- Each H fire is discrete. Outside RTH it is **clock-only** (no Git, no journal, no RH).
- Full H scan runs only 13:10–15:45 ET when flat.
- `scripts/run_phase2_cycle.py` is a **read-only** offline cycle. It does not place.

Profit’s “every 5 minutes while ON” therefore needs a **new** scheduler (separate Automation or other owner-approved runtime). It must not hitch onto H’s 15-minute fire or H’s outside-RTH clock-only rule.

## 7. Existing configuration system

| File | Purpose |
|---|---|
| `config/rules.json` | Canonical machine spec. `io_util.load_rules()` reads **only** this file |
| `config/autonomous_permissions.json` | H kill switch. `status: ACTIVE`. Allowed: option review/place/cancel. **Forbidden:** equity and crypto place/cancel, exercise |
| `pipeline/io_util.py` | JSON/JSONL helpers; `CONFIG` hard-wired to `rules.json` |

There is no `agent_profit` key, no Profit permissions file, and no Profit state store.

**Do not** put Profit numbers into `rules.json` → `agent_h`. That block is H-locked.

## 8. Existing risk engine

`pipeline/risk.py`:

- Options: −20% / +40% of premium, 1 contract
- Equity: −20% / +25% of cost, flatten-before-close, whole-share fields

`pipeline/equity_day_trade.py` `whole_share_size` sizes to buying power, not $50.

H daily loss is **1% of BOD NLV**, not $50, and is H-realized-option P/L.

**None of this is Agent Profit’s risk engine.** Reusing it would silently apply the wrong stops, targets, size, and session policy.

## 9. Existing logging

- `journal/*.md` and `*.jsonl` — H / F operational notes. Journal on **`main`** only.
- `pipeline/io_util.append_jsonl` — reusable mechanic.
- `signals/*` — historical snapshots, `do_not_place`. Never place from them.
- No decision/audit logger with Profit’s required fields.
- No secret-redaction logger (today the repo mostly avoids secrets by not having them).

## 10. Existing order-management code

- `pipeline/orders.py` — working-state sets for option and equity tickets. RH MCP has no `open=true` filter. **Reuse the state sets.**
- `pipeline/execution.py` — F dry builders; equity builder requires **integer shares** and `regular_hours`.
- H cancel / protect / TP / liquidation lives in the H prompt + `h_gates` / `h_closer`. Option-only. **Do not extend those modules to stocks.**

There is no live Python broker adapter. The LLM calls MCP.

## 11. Existing position-management code

- Broker is authoritative. H reconstructs leftover from option positions + working orders.
- `get_equity_positions` is on H’s required-tool list **for occupancy**, not for H to manage shares.
- No ownership ledger. No “this share lot belongs to F / H / Profit” store.
- Unmarked equity (F leftovers, manual buys, corporate actions) must be treated as **do not touch**.

## 12. Existing ON/OFF mechanisms

| Actor | Off | On |
|---|---|---|
| H | Disable the Automation, or `config/autonomous_permissions.json` missing / `status` not `ACTIVE` | Automation enabled + permissions ACTIVE. H must not self-enable |
| F | Always supervised; `can_place_live` / `f_may_place` | Specific-order confirm in this chat |
| Profit | **Does not exist** | — |

H inactive permissions still allow cancel / protect / reduce / close of **H exposure**. They forbid equity tools, so H cannot flatten Profit stock even if asked by a confused prompt.

---

## KEEP — reusable as-is (import, do not fork-edit)

- Official RH MCP **equity** tool names (after live schema verify).
- `pipeline/io_util.py` — `read_json` / `write_json` / `append_jsonl` / `utc_now_iso`. Add a **new** Profit loader; do not change `load_rules()`.
- `pipeline/orders.py` — `EQUITY_WORKING_STATES`, `is_working_equity_state`, `normalize_state`.
- Bid/ask parsing ideas in `equity_day_trade.parse_bid_ask` / `equity_quote_ok` and `quotes._positive_money` / `_parse_ts` — copy or import the **pure parsers** only.
- `pipeline/news.py` — factual headline packaging.
- `pipeline/universe.py` crypto / index skip; object-type constants.
- `pipeline/ticks.py` `EQUITY_TICK` ($0.01) for stock stops/limits when `min_ticks` is absent for equities.
- Inverse-ETF symbol list as a **partial** “not a single-name stock” signal. Profit still needs a full ETF/ETN/fund classifier; this list is not sufficient.
- Account convention: Agentic last4 `2907` only; mask in user text; full number only in RH tool args.
- Fail-closed culture: missing tool / stale quote / unknown state → no new order.
- `requirements.txt` — `numpy`, `pytest`. No new brokerage dependency required.

## REFACTOR — additive only, after approval

These are **new files or tiny non-behavioral additions**. They are not rewrites of H.

- New Profit config loader (do not overload `load_rules()`).
- New session engine (do not expand `pipeline/session.py` into Profit’s calendar; H tests lock that clock).
- New stock-only + no-ETF classifier (do not change `apply_liquidity_filter` to reject all ETFs; that would break F’s long-ETF playbook).
- New fractional / `$50` sizer (do not change `whole_share_size`).
- README / `agents/README.md` / `AGENTS.md` **pointers** after the package exists: F still supervised; H still options; Profit is a third actor.
- Optional later: a **separate** owner-approved H occupancy exception. **Not in the first Profit build.**

## NEW — Profit must create

Isolated package (names follow this repo, not the spec’s nested tree blindly):

```text
agent_profit/
  __init__.py
  cli.py                         # prints startup / scan / risk / order cards; never calls MCP
  config_loader.py               # load + validate Profit JSON only
  strategy/
    scanner.py                   # 5-minute opportunity pass (candidates, not orders)
    stock_selector.py            # stock-only universe filter
    technical_analysis.py        # indicators from verified bars / RH technicals
    catalyst_analysis.py         # news / earnings / SEC packs; mark UNKNOWN if missing
    decision_engine.py           # AI-facing proposal object (not authority)
    playbook_filter.py           # strip options / short / ETF advice
  risk/
    risk_engine.py               # final PASS / REJECT
    position_sizer.py            # ≤ $50, fractional if tradability says so
    daily_loss.py                # $50 Profit-attributed realized loss → SAFE MODE
    position_limits.py           # ≤ 5 Profit-owned positions; no duplicate ticker
    trade_validator.py           # long-only, stock-only, no short, no ETF, no options
  execution/
    broker_port.py               # documented MCP argument builders + parse helpers
    order_manager.py             # idempotent ref_id / client-order tracking
    order_validator.py           # pre-place independent checks
    fill_reconciler.py           # never assume timeout = no fill
  market/
    session_engine.py            # premarket / RTH / AH / overnight / closed / holiday
    quote_quality.py             # freshness, spread, one-sided, crossed
    liquidity.py                 # volume / depth / session tradability
    calendar.py                  # fail closed if holiday/special session UNKNOWN
    instrument_class.py          # stock vs ETF / ETN / fund / warrant / ADR policy
  monitoring/
    position_monitor.py          # broker-authoritative marks
    exits.py                     # +10% TP and −50% SL from **average fill**, not ticket
  state/
    state_manager.py
    ownership_ledger.py          # Profit order ids ↔ lots; unmarked = do not touch
    reconciliation.py
  logging/
    decision_logger.py
    trade_logger.py
    audit_logger.py              # redacts secrets by key name
  tests/                         # pytest; no live MCP

config/agent_profit/
  rules.json                     # spec defaults, validated
  risk.json                      # numerical limits (duplicated in rules, cross-checked)
  sessions.json                  # documented RH windows + UNKNOWN flags
  universe.json                  # scan sources; no min-price rule
  autonomous_permissions.json    # Profit kill switch; default OFF

playbooks/agent_profit_autonomous.PROMPT.md   # created only after owner approval
journal/agent_profit/            # Profit identity on every row; not H lease/session
```

## DO NOT TOUCH

Do not edit these while creating Agent Profit (unless the owner later opens a **separate** H change):

- `pipeline/f_attention.py`
- `pipeline/execution.py`
- `config/rules.json` (especially `agent_h`, `risk.equity`, `execution.agent_f`)
- `config/autonomous_permissions.json` (H allowlist / forbidden equity tools)
- `pipeline/h_gates.py`, `h_dispatch.py`, `h_attention.py`, `h_budget.py`, `h_continuity.py`, `h_closer.py`, `h_failures.py`, `h_invariants.py`
- `playbooks/agent_h_autonomous.PROMPT.md` (do not paste into this chat; do not add Profit text)
- `pipeline/session.py` H clock
- `pipeline/equity_day_trade.py` whole-share / RTH / long-ETF path
- `pipeline/risk.py` H/F percentages
- `journal/h_lease.json` / `journal/h_session.json` conventions
- H Automation id `9af478e7-a454-11f1-a7d1-d6b4613131ce` prompt in Cursor

---

## Functions / classes to reuse

| Symbol | Use |
|---|---|
| `io_util.read_json` / `write_json` / `append_jsonl` / `utc_now_iso` | I/O |
| `orders.EQUITY_WORKING_STATES` / `is_working_equity_state` | Duplicate / working-ticket detection |
| `equity_day_trade.parse_bid_ask` / `equity_quote_ok` | Quote sanity (not session policy) |
| `equity_day_trade.is_inverse_etf` / `INVERSE_ETF_SYMBOLS` | Extra reject signal only |
| `equity_day_trade.buying_power_from_raw` | Buying-power parse |
| `quotes._parse_ts` / age helpers | Quote freshness |
| `news.build_news_signal` | Catalyst pack |
| `universe.extract_watchlist_symbols` | Optional seed list; then Profit stock filter |
| `ticks.EQUITY_TICK` / `protective_stop_price` | Tick rounding for stock exits |
| `session.now_et` / `today_et` | ET clock helpers only |

## Functions / classes to create

| Symbol | Job |
|---|---|
| `load_profit_rules()` / `validate_profit_config()` | Startup fail-closed |
| `ProfitSessionEngine.classify()` | Session + holiday UNKNOWN |
| `classify_instrument()` | Individual stock vs prohibited |
| `size_long_stock()` | `min(50.00, buying_power)` notional; fractional if allowed |
| `ProfitRiskEngine.review_entry()` | Hard numeric + legal gates |
| `ProfitRiskEngine.review_exit()` | +10% / −50% from **fill**; AI cannot widen/skip |
| `OwnershipLedger` | Register only Profit fills; refuse unmarked sells |
| `IdempotencyStore` | `ref_id` / intent key; timeout → reconcile, never re-place |
| `DailyLossTracker` | Profit-attributed realized P/L only; $50 → SAFE MODE |
| `print_profit_card()` | One-fire instruction card (H-style, Profit identity) |

---

## Configuration (initial, validated, default OFF)

New file `config/agent_profit/rules.json` (not `rules.json` → `agent_h`):

```json
{
  "schema_version": "2026-10-06.0-draft",
  "agent": "profit",
  "account_number_last4": "2907",
  "agent_profit_enabled": false,
  "auto_enable_on_restart": false,
  "asset_class": "stocks",
  "direction": "long_only",
  "allow_etfs": false,
  "allow_options": false,
  "allow_short": false,
  "allow_crypto": false,
  "allow_index": false,
  "allow_warrants": false,
  "allow_otc": false,
  "max_trade_value": 50.00,
  "max_open_positions": 5,
  "max_daily_loss": 50.00,
  "position_stop_loss_percent": 50.0,
  "take_profit_percent": 10.0,
  "fractional_shares": true,
  "scan_interval_minutes": 5,
  "allow_premarket": true,
  "allow_regular_hours": true,
  "allow_after_hours": true,
  "allow_24_hour": true,
  "allow_earnings": true,
  "allow_news": true,
  "autonomous_execution": true,
  "daily_loss_reset": "next_et_trading_date",
  "unmarked_equity_policy": "do_not_touch"
}
```

Validation (reject, do not coerce):

- Booleans must be booleans; money fields must be exactly `50.00` / `50.0` / `10.0` as specified unless the owner later changes them.
- `direction` must be `long_only`.
- `allow_etfs`, `allow_options`, `allow_short`, `allow_crypto` must be `false`.
- `max_trade_value` must be `<= 50` and `> 0`.
- `max_open_positions` must be `1..5`.
- `auto_enable_on_restart` must be `false` unless the owner later sets it.
- `agent_profit_enabled` default `false`. A restart reads persisted state; it does **not** flip ON.

`config/agent_profit/autonomous_permissions.json` (new file):

- `status`: `INACTIVE` by default (OFF).
- `allowed_place_tools`: `review_equity_order`, `place_equity_order`, `cancel_equity_order` only — and only when status is `ACTIVE` **and** persisted ON is true.
- `forbidden_place_tools`: all option place/exercise, all crypto, `sell_short` if it appears.
- Does **not** replace H’s permissions file.

## Dependencies

- Existing: `numpy`, `pytest`.
- No Robinhood SDK.
- No new secrets in git.
- Optional later: a verified market-holiday source. Until then, session = RH tradability + documented RH windows; holiday/special = UNKNOWN → no new entry.

## Security

Inspected this repo (names only, no values printed):

| Item | Present in repo? | Where referenced | Required? | Keep? |
|---|---|---|---|---|
| RH MCP Cursor auth | Not in git (runtime `needsAuth`) | Cursor MCP, not a file | Yes, for live Profit | Remain outside git |
| API keys / tokens / passwords | **No** `.env`, no MCP JSON | — | MCP is Cursor-side | Do not add |
| `account_number_last4` | Yes, `2907` | `config/rules.json`, H permissions | Identify account | Keep; mask in logs |
| Full account number | **No** | RH tool args only at runtime | Yes, at place time | Never log / commit |
| H Automation id | Yes | `rules.json`, permissions, README | H only | Do not reuse for Profit |

Log redaction must drop keys matching `token`, `secret`, `password`, `authorization`, `api_key`, `account_number` (full). Keep `account_number_last4`.

---

## Broker / MCP requirements (Profit)

**Allowed when ON and card = PASS:**

- Reads: accounts, portfolio, equity positions/orders/quotes/historicals/fundamentals/tradability/news/price book/technicals, earnings, SEC, scanners, search, realized P/L (for **attribution**, not as a substitute for Profit’s own fill ledger).
- Writes: `review_equity_order` → `place_equity_order` → `cancel_equity_order` for **Profit-owned** long stock only.

**Never:**

- `place_option_order`, `exercise_option`, crypto tools, `sell_short`, index-only instruments.

**Per-order verify (fail closed):**

1. Profit persisted state is ON and permissions ACTIVE.
2. Instrument classified as an individual U.S. stock (not ETF/ETN/fund/warrant/option/crypto/index).
3. Side is `buy` for entries; `sell` only against a Profit-owned long quantity.
4. Intended notional ≤ $50.00 (hard; `50.01` reject).
5. Profit-owned open positions < 5 (broker + ledger agree; if they disagree → SAFE MODE, no new entry).
6. No duplicate open Profit position or working **buy** in the same ticker.
7. Daily Profit-attributed realized loss < $50.00.
8. `get_equity_tradability` confirms the **current** session, fractional eligibility, and buy/sell.
9. Quote fresh enough (configurable; start from H’s 5s equity idea, relax only with a measured extended-hours policy — do not trade stale).
10. Spread / one-sided / crossed checks pass (stricter in extended/overnight, not disabled).
11. Buying power ≥ intended notional.
12. Session supported: RTH / extended / 24h only if **both** broker session and that security support it.
13. 24h: whole-share **limit** only per official RH 24 Hour Market page. If `$50` cannot buy 1 share, **do not** invent a fractional 24h ticket.
14. Extended hours: **limit** only. Market/stop in extended/overnight **queue for RTH** per official RH — do not use them as “now” exits.
15. `review_equity_order` `order_checks` block → do not place.
16. After any timeout: `get_equity_orders` / positions first. Never assume failure.

**Stops and targets:**

- Compute stop and target from **average fill**, not the limit ticket.
- +10% → deterministic sell of the Profit quantity.
- −50% → deterministic sell of the Profit quantity.
- AI cannot widen, remove, or override.
- Because RH market/stop tickets in extended/overnight queue for the regular open, Profit must **monitor and sell with a session-valid limit** when the hard exit triggers outside RTH. Do not rest a full-quantity TP against a working full-quantity stop (same cancel-confirm rule as F/H).

## ON/OFF architecture

```text
Cursor Automation (new, not H)
        │
        ▼
python -m agent_profit.cli card
        │
        ▼
config/agent_profit/autonomous_permissions.json   status ACTIVE|INACTIVE
        AND
persisted state.agent_profit_enabled true|false
        AND
not SAFE MODE (unless managing existing Profit exits)
        │
        ▼
ON  = scan + propose + (if PASS) review/place + monitor Profit lots
OFF = no scan strategy, no new tickets, no autonomous place
```

- Default **OFF**. `auto_enable_on_restart: false`.
- Visible: every card and log line includes `profit_enabled=` and `safe_mode=`.
- Kill switches (any one sufficient for no **new** entry): permissions not ACTIVE; persisted OFF; daily-loss SAFE MODE; owner “stop all Profit order activity”.
- SAFE MODE: cancel **Profit entry** working buys; keep monitoring Profit positions; still allow deterministic TP/SL sells of Profit lots; no new entries until the next ET trading date per `daily_loss_reset`.
- Restart: load config → validate → read ON/OFF → connect (if ON or leftover Profit) → reconcile broker → classify session → attribute ownership → compute daily P/L → **then** scan. Never place because the process started.
- F chat remains supervised. F must not “turn on” Profit by placing. F may later have a **specific** owner command to flip the persisted flag; that is not this PR.

## Agent H isolation strategy

| Rule | Enforcement |
|---|---|
| Separate config | `config/agent_profit/*` only |
| Separate state / logs | `journal/agent_profit/*`; every row `agent: "profit"` |
| Separate Automation | New id when the owner creates it. Do not reuse H’s id or prompt |
| Separate risk numbers | Never read `rules.json` → `agent_h` for size/stop/TP/daily loss |
| Profit never sells H options | Profit must not call option place/cancel/exercise |
| H never sells Profit stock | Already true: H forbidden equity tools. Do not add equity tools to H |
| Profit never sells unmarked equity | Ownership ledger miss → reject sell |
| Position count | Count **Profit-owned** lots + Profit working **opens** only. H options do not fill a Profit slot |
| Daily loss | Sum **Profit** closed fills that session, not account-wide `get_realized_pnl` unless it can be filtered and verified |
| Buying power | Shared. Profit still caps at $50 and must re-read `get_portfolio` immediately before review/place |
| Occupancy side-effect | Unchanged H rule: Profit stock **blocks H new entries**. Documented above; not “fixed” in this plan |
| F leftovers | Do not touch |
| Playbooks | Filter: if a playbook implies options, shorts, or ETFs, drop that advice |

If ownership cannot be determined: **do not modify the position.**

---

## Trade pipeline (after approval)

```text
STARTUP reconcile (no place)
    → every 5 minutes while ON
MARKET SCAN (watchlists + official scanners + tradability)
    → STOCK-ONLY + LIQUIDITY + SESSION filter
    → technical + catalyst packs (UNKNOWN if missing)
    → AI ranks / proposes (rationale only)
    → DETERMINISTIC RISK ENGINE
    → PASS / REJECT (logged)
    → ORDER VALIDATOR
    → fresh quote + session + duplicate + broker review
    → place only the printed card
    → FILL VERIFY (broker)
    → register ownership + stop/target from fill
    → monitor: +10% sell / −50% sell
```

A scan is not a trade. Most 5-minute fires should reject.

## Startup sequence (when implemented)

1. Load + validate `config/agent_profit/*`.
2. Read persisted ON/OFF (`auto_enable_on_restart` false).
3. If OFF and no Profit leftover: log OFF and exit. No RH writes.
4. If ON or leftover: `get_accounts` (••••2907 only), `get_portfolio`, equity positions, equity orders.
5. Reconcile ledger vs broker. Mismatch → SAFE MODE, no new entry.
6. Classify session (UNKNOWN holiday → no new entry).
7. Compute Profit daily P/L. If ≤ −$50 → SAFE MODE, cancel Profit entry orders.
8. Only then scan.

## Failure mode

| Condition | Action |
|---|---|
| Market data down / quote stale | No trade |
| MCP/auth down | No new orders |
| Position/order pages incomplete | No conflicting order |
| Ownership unknown | Do not modify |
| Config invalid | Refuse start |
| Unknown state | SAFE MODE |

## Logging (required fields)

**Every candidate:** timestamp, symbol, session, price, volume/liquidity, news/catalyst or UNKNOWN, technical summary, AI rationale summary, proposed action, risk result, rejection reason.

**Every trade:** symbol, buy/sell, qty (fractional ok), intended value, actual fill, fill price, timestamp, position id, strategy, target, stop, result.

Never log secrets.

---

## Phased build (only after this plan is approved)

**Phase A — skeleton, still OFF.** Package + config validation + tests. No MCP auth. No Automation. No `place_*`.

**Phase B — deterministic core.** Sizer, instrument class, session engine, risk engine, ownership, idempotency, daily loss, exit math. Fixture tests only.

**Phase C — dry broker port.** Argument builders + parsers aligned to **live** official schemas after owner-approved `mcp_auth` in a non-placing session. Still no place.

**Phase D — prompt + Automation.** `playbooks/agent_profit_autonomous.PROMPT.md`. Owner creates a **new** Automation, 5-minute cadence, permissions INACTIVE until the owner flips ON.

**Phase E — paper-like shadow.** ON but `autonomous_execution: false` (log PASS cards, do not place) for an owner-chosen period.

**Phase F — live.** Owner sets permissions ACTIVE + persisted ON. First live day: max 1 position until the owner says otherwise (optional extra gate; default spec is 5).

No phase edits H locks.

---

## Files this approval-PR may contain

| Path | Action |
|---|---|
| `docs/agent_profit_implementation_plan.md` | **Create** (this file) |

## Files to create after approval (not in this PR)

See the `agent_profit/` tree above, plus `config/agent_profit/*`, `playbooks/agent_profit_autonomous.PROMPT.md`, `journal/agent_profit/.gitkeep`, Profit pytest files.

## Files to modify after approval (minimal pointers only)

| Path | Change |
|---|---|
| `README.md` | Add a “Who places” row for Profit; keep H and F rows unchanged |
| `agents/README.md` | One-line pointer to Profit |
| `AGENTS.md` | One-line: F does not run Profit; Profit is a separate OFF-by-default actor |

Do not modify H lock files for those pointers.

## Files to leave untouched

Everything under `pipeline/h_*.py`, `pipeline/f_attention.py`, `pipeline/execution.py`, `config/rules.json`, `config/autonomous_permissions.json`, `playbooks/agent_h_autonomous.PROMPT.md`, H journal lease/session.

---

## What this chat will not do until you approve

- Create the `agent_profit/` package
- Change Agent H rules, prompt, occupancy, or permissions
- Authenticate Robinhood MCP
- Call `place_*` / `cancel_*`
- Turn anything ON
- Convert F’s equity playbook into Profit
- Treat 04:00 ET as Robinhood premarket
- Assume every symbol is 24h or fractional
- Count H options toward Profit’s 5 slots, or let Profit sell unmarked stock

**Agent Profit authority (unchanged):** buy liquid individual U.S. stocks long only, up to $50 per entry, maximum 5 Profit positions, $50 daily Profit loss limit, 50% hard stop and 10% automatic target from actual fill, only in broker-supported sessions, AI selection + deterministic risk.

Everything else stays prohibited unless you explicitly change the specification.
