# Agents (Phase 3)

Phase 2 remains the signal pipeline. Phase 3 adds **Agent F** dry review.

Options playbook is **RELEASED**. Equities day-trading playbook is **DRAFT** (`playbooks/equities_day_trading.md`) — not implemented, not a place-authorization. **No** `place_*` until an explicit confirm of a **specific** order in this Cursor chat.

| Agent | Module | Output |
|---|---|---|
| A–E + I | `pipeline/*` | `signals/*` |
| F Supervised | `pipeline/execution.py` | `signals/execution_review.json`, `journal/reviews.jsonl` |
| G Loop | `pipeline/orchestrator.py` | `journal/loop_runs.jsonl` |
| H Unsupervised | `playbooks/agent_h_autonomous.PROMPT.md` | **ON** — Automation [Agentic AI Bot](https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce). Disable there to stop. |

## Run
1. Assemble RH MCP dumps into `data/raw/latest_raw.json`
2. `python3 scripts/run_phase2_cycle.py`
3. Review `signals/phase2_summary.json`
