# RTH-only session lock — copy everything below the line

Paste this as the **first** block in a Cursor Automation prompt (or replace the Session section in Agent H).

---

## Session lock (owner, 2026-08-30) — RTH only

Clock: **America/New_York**.

**Normal market hours (RTH):** Monday–Friday, **09:30:00 through 16:00:00** Eastern, only on days the US cash equity session is open.

**Not allowed:** pre-market, after-hours, overnight, weekends, US market holidays, early-close *after* that day’s cash close.

### Scan
- **Only** scan the market during RTH.
- If now is outside RTH: **stop**. Do not call watchlists, historicals, chains, quotes, news, or scanners. Journal one line: `skipped: outside_rth` and exit.

### Buy
- **Only** purchase options or equities during RTH.
- Every `review_*` / `place_*` buy-to-open must use `market_hours=regular_hours`.
- If now is outside RTH: **do not** `review_*` or `place_*` for a new buy.
- Do not place extended-hours, all-day, curb, or overnight entry orders.

### If this Automation fires outside RTH
Exit immediately. No scan. No buy.
