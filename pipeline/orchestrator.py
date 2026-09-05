from __future__ import annotations

from collections import Counter
from typing import Any

from pipeline.equity_day_trade import buying_power_from_raw, select_equity_day_trade_candidates
from pipeline.greeks import delta_in_band, extract_greeks
from pipeline.io_util import append_jsonl, load_rules, utc_now_iso, write_json, SIGNALS, JOURNAL
from pipeline.news import build_news_signal
from pipeline.options_structure import (
    choose_structure_from_bias,
    instrument_id,
    rank_atm_then_one_otm,
    rank_expirations,
    strikes_bracket_spot,
)
from pipeline.patterns import collect_pattern_hits
from pipeline.risk import equity_risk_plan, options_risk_plan
from pipeline.session import today_et
from pipeline.universe import apply_liquidity_filter, extract_watchlist_symbols, option_quote_liquid


def dominant_bias(pattern_hits: list[dict[str, Any]]) -> str | None:
    biases = [p.get("bias") for p in pattern_hits if p.get("bias") in ("bullish", "bearish")]
    if not biases:
        return None
    counts = Counter(biases)
    # Require strict majority
    top, n = counts.most_common(1)[0]
    if n > len(biases) / 2:
        return top
    return None


def _snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "do_not_place": True,
        "snapshot_note": "Pipeline snapshot. Re-quote live. Never place from this file.",
    }


def _option_premium(quote: dict[str, Any], liq_metrics: dict[str, Any]) -> tuple[float | None, str | None]:
    """Playbook premium is bid/ask mid. Do not require mark_price."""
    mid = liq_metrics.get("mid")
    if mid not in (None, ""):
        try:
            value = float(mid)
            if value > 0:
                return value, "mid"
        except (TypeError, ValueError):
            pass
    for key in ("mark_price", "adjusted_mark_price"):
        if quote.get(key) not in (None, ""):
            try:
                value = float(quote[key])
                if value > 0:
                    return value, key
            except (TypeError, ValueError):
                continue
    return None, None


def run_pipeline(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Phase 2 orchestrator.
    `raw` is assembled by the Cursor agent from RH MCP responses (read-only).
    Never places orders.
    """
    rules = load_rules()
    as_of = utc_now_iso()
    assert rules["execution"]["phase2_places_orders"] is False

    # --- Agent A ---
    universe_extract = extract_watchlist_symbols(
        raw.get("watchlists", []),
        raw.get("watchlist_items_by_id", {}),
        raw.get("option_watchlist_items"),
        include_crypto=rules["universe"]["include_crypto"],
        include_options_watchlist=rules["universe"]["include_options_watchlist"],
    )
    liq = apply_liquidity_filter(
        universe_extract["equity_symbols"],
        raw.get("fundamentals_by_symbol", {}),
        min_average_volume=float(rules["liquidity"]["min_average_volume"]),
    )
    universe_signal = {
        "agent": "A_scanner",
        "as_of": as_of,
        "mode": "read_only",
        "extract": universe_extract,
        "liquidity": liq,
        "index_symbols": universe_extract["index_symbols"],
        "eligible_equities": liq["passed_symbols"],
    }
    write_json(SIGNALS / "universe.json", _snapshot(universe_signal))

    # --- Agent B ---
    technicals: dict[str, Any] = {"agent": "B_patterns", "as_of": as_of, "symbols": {}}
    historicals = raw.get("historicals_by_symbol_timeframe", {})
    for symbol in liq["passed_symbols"]:
        symbol_hits = collect_pattern_hits(
            historicals.get(symbol) or {},
            list(rules["patterns"]["timeframes"]),
        )
        technicals["symbols"][symbol] = {
            "pattern_hits": symbol_hits,
            "dominant_bias": dominant_bias(symbol_hits),
        }
    write_json(SIGNALS / "technicals.json", _snapshot(technicals))

    # --- Agent C ---
    news_signal = {"agent": "C_news", "as_of": as_of, "symbols": {}}
    news_raw = raw.get("news_by_symbol", {})
    earnings_raw = raw.get("earnings_by_symbol", {})
    for symbol in liq["passed_symbols"]:
        news_signal["symbols"][symbol] = build_news_signal(
            symbol,
            news_raw.get(symbol) or [],
            earnings_raw.get(symbol),
        )
    write_json(SIGNALS / "news.json", _snapshot(news_signal))

    # --- Agents D + I ---
    option_candidates: list[dict[str, Any]] = []
    greeks_rows: list[dict[str, Any]] = []
    equity_fallbacks: list[dict[str, Any]] = []
    spots = raw.get("spots_by_symbol", {})
    chains = raw.get("option_chains_by_symbol", {})
    instruments_by_key = raw.get("option_instruments_by_symbol_exp", {})
    quotes_by_id = raw.get("option_quotes_by_id", {})
    quotes_by_id = {str(k): v for k, v in quotes_by_id.items()}
    buying_power = buying_power_from_raw(raw)
    delta_lo = float(rules["options"]["strike"]["delta_min"])
    delta_hi = float(rules["options"]["strike"]["delta_max"])
    max_spread = float(rules["liquidity"]["option_max_spread_pct_of_price"])
    pref_spread = float(rules["liquidity"]["option_preferred_spread_pct_of_price"])
    reject_one_sided = bool(rules["liquidity"]["reject_one_sided_quotes"])
    multiplier = 100.0
    min_dte = int(rules["options"].get("min_dte", 0))
    max_dte = int(rules["options"]["max_dte"])
    overnight_holding = bool(rules["agent_h"].get("overnight_holding_enabled", False))

    for symbol in liq["passed_symbols"]:
        bias = technicals["symbols"].get(symbol, {}).get("dominant_bias")
        structure = choose_structure_from_bias(bias)
        spot = spots.get(symbol)
        if structure is None or spot is None:
            equity_fallbacks.append(
                {
                    "symbol": symbol,
                    "reason": "no_directional_bias_or_spot" if structure is None else "missing_spot",
                    "bias": bias,
                }
            )
            continue

        chain = chains.get(symbol) or {}
        expirations = rank_expirations(
            chain.get("expiration_dates") or [],
            overnight_holding_enabled=overnight_holding,
            hard_min_dte=min_dte,
            hard_max_dte=max_dte,
        )
        if not expirations:
            equity_fallbacks.append({"symbol": symbol, "reason": "no_expiration_within_max_dte", "bias": bias})
            continue

        option_type = "call" if structure == "long_call" else "put"
        passed: dict[str, Any] | None = None
        last_reject: dict[str, Any] | None = None
        for exp in expirations:
            instruments = instruments_by_key.get(f"{symbol}|{exp}") or instruments_by_key.get(symbol) or []
            if not strikes_bracket_spot(float(spot), instruments, option_type=option_type):
                last_reject = {
                    "symbol": symbol,
                    "reason": "option_chain_incomplete_atm_not_in_page",
                    "bias": bias,
                    "expiration": exp,
                }
                continue

            ranked = rank_atm_then_one_otm(float(spot), instruments, option_type=option_type)
            if not ranked:
                last_reject = {"symbol": symbol, "reason": "no_instrument_match", "bias": bias, "expiration": exp}
                continue

            for pick in ranked:
                inst = pick["instrument"]
                oid = instrument_id(inst)
                if not oid:
                    last_reject = {"symbol": symbol, "reason": "missing_option_id", "bias": bias, "expiration": exp}
                    continue
                quote = quotes_by_id.get(oid) or quotes_by_id.get(str(inst.get("id"))) or {}
                ok_liq, liq_reason, liq_metrics = option_quote_liquid(
                    quote,
                    max_spread_pct_of_price=max_spread,
                    preferred_spread_pct_of_price=pref_spread,
                    reject_one_sided=reject_one_sided,
                )
                gpack = extract_greeks(quote)
                greeks_rows.append(
                    {
                        "symbol": symbol,
                        "option_id": oid,
                        "expiration": exp,
                        "type": option_type,
                        "strike": inst.get("strike_price", inst.get("strike")),
                        "selection": pick["selection"],
                        **gpack,
                        "liquidity": {"ok": ok_liq, "reason": liq_reason, **liq_metrics},
                    }
                )
                if not ok_liq:
                    last_reject = {
                        "symbol": symbol,
                        "reason": f"option_illiquid:{liq_reason}",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                ok_delta, delta_reason = delta_in_band(
                    gpack["greeks"].get("delta"),
                    option_type=option_type,
                    lo=delta_lo,
                    hi=delta_hi,
                )
                if not ok_delta:
                    last_reject = {
                        "symbol": symbol,
                        "reason": f"greeks_filter:{delta_reason}",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                premium, premium_source = _option_premium(quote, liq_metrics)
                if premium is None:
                    last_reject = {
                        "symbol": symbol,
                        "reason": "missing_bid_ask_mid",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                cash = premium * multiplier
                if buying_power is None:
                    last_reject = {
                        "symbol": symbol,
                        "reason": "missing_buying_power",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                    }
                    continue
                if cash > buying_power + 1e-9:
                    last_reject = {
                        "symbol": symbol,
                        "reason": "exceeds_buying_power",
                        "bias": bias,
                        "option_id": oid,
                        "selection": pick["selection"],
                        "expiration": exp,
                        "cash_debit": cash,
                        "buying_power": buying_power,
                    }
                    continue
                passed = {
                    "symbol": symbol,
                    "structure": structure,
                    "bias": bias,
                    "expiration": exp,
                    "option_type": option_type,
                    "strike": inst.get("strike_price", inst.get("strike")),
                    "option_id": oid,
                    "selection": pick["selection"],
                    "premium_mark": premium,
                    "premium_source": premium_source,
                    "greeks": gpack["greeks"],
                    "liquidity": liq_metrics,
                    "contracts": 1,
                    "cash_debit": cash,
                    "playbook_status": rules["options"]["playbook_status"],
                }
                break
            if passed is not None:
                break

        if passed is None:
            equity_fallbacks.append(last_reject or {"symbol": symbol, "reason": "no_instrument_match", "bias": bias})
            continue
        option_candidates.append(passed)

    write_json(
        SIGNALS / "option_candidates.json",
        _snapshot(
            {
                "agent": "D_option_structure",
                "as_of": as_of,
                "mode": "read_only",
                "candidates": option_candidates,
                "equity_fallbacks": equity_fallbacks,
                "max_contracts": rules["options"]["max_contracts"],
            }
        ),
    )
    write_json(
        SIGNALS / "greeks.json",
        _snapshot({"agent": "I_greeks", "as_of": as_of, "source": "robinhood_get_option_quotes", "rows": greeks_rows}),
    )

    equity_candidates, equity_rejects = select_equity_day_trade_candidates(
        symbols=liq["passed_symbols"],
        technicals_by_symbol=technicals["symbols"],
        option_candidate_symbols={c["symbol"] for c in option_candidates},
        quotes_by_symbol=raw.get("equity_quotes_by_symbol") or {},
        tradability_by_symbol=raw.get("equity_tradability_by_symbol") or {},
        fundamentals_by_symbol=raw.get("fundamentals_by_symbol") or {},
        buying_power=buying_power,
        playbook_status=str(rules["risk"]["equity"]["playbook_status"]),
        take_profit_pct=float(rules["risk"]["equity"]["take_profit_pct_of_cost"]),
        stop_loss_pct=float(rules["risk"]["equity"]["stop_loss_pct_of_cost"]),
    )
    write_json(
        SIGNALS / "equity_candidates.json",
        _snapshot(
            {
                "agent": "D_equity_day_trade",
                "as_of": as_of,
                "mode": "read_only",
                "playbook_status": rules["risk"]["equity"]["playbook_status"],
                "playbook_path": rules["risk"]["equity"]["playbook_path"],
                "side": "long_only",
                "no_shorting": True,
                "priority": "options_first",
                "candidates": equity_candidates,
                "rejected": equity_rejects,
                "option_fallback_notes": equity_fallbacks,
            }
        ),
    )

    # --- Agent E ---
    risk_plans: list[dict[str, Any]] = []
    for cand in option_candidates:
        plan = options_risk_plan(
            premium_per_share=float(cand["premium_mark"]),
            contracts=1,
            take_profit_pct=float(rules["risk"]["options"]["take_profit_pct_of_cash"]),
            stop_loss_pct=float(rules["risk"]["options"]["stop_loss_pct_of_cash"]),
        )
        risk_plans.append({"symbol": cand["symbol"], "option_id": cand["option_id"], **plan})

    # Equity fallback risk plans only when explicitly provided cost basis in raw (optional)
    for fb in raw.get("equity_fallback_costs", []) or []:
        plan = equity_risk_plan(
            cost_basis=float(fb["cost_basis"]),
            take_profit_pct=float(rules["risk"]["equity"]["take_profit_pct_of_cost"]),
            stop_loss_pct=float(rules["risk"]["equity"]["stop_loss_pct_of_cost"]),
        )
        risk_plans.append({"symbol": fb["symbol"], **plan})

    for cand in equity_candidates:
        risk_plans.append({"symbol": cand["symbol"], **cand["risk"]})

    write_json(
        SIGNALS / "risk_plan.json",
        _snapshot(
            {
                "agent": "E_risk",
                "as_of": as_of,
                "mode": "read_only",
                "max_open_positions": rules["risk"]["max_open_positions"],
                "plans": risk_plans,
                "notes": "Stop-first until OCO; TP monitored in loop. Phase 2 does not place orders.",
            }
        ),
    )

    summary = {
        "as_of": as_of,
        "phase": 2,
        "places_orders": False,
        "eligible_equities": liq["passed_symbols"],
        "option_candidate_count": len(option_candidates),
        "equity_candidate_count": len(equity_candidates),
        "equity_fallback_count": len(equity_fallbacks),
        "risk_plan_count": len(risk_plans),
        "open_questions": rules.get("open_questions", []),
    }
    write_json(SIGNALS / "phase2_summary.json", _snapshot(summary))
    append_jsonl(
        JOURNAL / "loop_runs.jsonl",
        {"event": "phase2_cycle", "mode": "read_only", **summary},
    )
    journal_day = today_et().isoformat()
    append_jsonl(
        JOURNAL / f"{journal_day}.md.jsonl",
        {"type": "markdown_seed", "text": f"# {journal_day} Phase 2 cycle\n\n- options candidates: {len(option_candidates)}\n- eligible equities: {len(liq['passed_symbols'])}\n"},
    )
    md_path = JOURNAL / f"{journal_day}.md"
    prev = md_path.read_text(encoding="utf-8") if md_path.exists() else f"# Trading journal {journal_day}\n\n"
    prev += f"\n## Phase 2 read-only cycle ({as_of})\n"
    prev += f"- Eligible equities: {', '.join(liq['passed_symbols']) or '(none)'}\n"
    prev += f"- Option candidates: {len(option_candidates)}\n"
    prev += f"- Equity day-trade candidates: {len(equity_candidates)}\n"
    prev += f"- Equity fallbacks (option miss): {len(equity_fallbacks)}\n"
    prev += "- Orders placed: **none** (Phase 2 read-only)\n"
    md_path.write_text(prev, encoding="utf-8")

    return summary
