# Agents (Phase 2)

Phase 2 is **read-only**. Agents write `signals/` + `journal/` only. **No** `place_*` / `cancel_*` calls.

| Agent | Module | Output |
|---|---|---|
| A Scanner | `pipeline/universe.py` | `signals/universe.json` |
| B Patterns | `pipeline/patterns.py` | `signals/technicals.json` |
| C News | `pipeline/news.py` | `signals/news.json` |
| D Structure | `pipeline/options_structure.py` | `signals/option_candidates.json` |
| I Greeks | `pipeline/greeks.py` | `signals/greeks.json` |
| E Risk | `pipeline/risk.py` | `signals/risk_plan.json` |
| G Loop | `pipeline/orchestrator.py` | `journal/loop_runs.jsonl` |
| F / H | (Phase 3 / 5) | not active |

## Run
1. Assemble RH MCP dumps into `data/raw/latest_raw.json`
2. `python3 scripts/run_phase2_cycle.py`
3. Review `signals/phase2_summary.json`
