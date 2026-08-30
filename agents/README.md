# Agents (Phase 3)

Phase 2 remains the signal pipeline. Phase 3 adds **Agent F** dry review.

**No** `place_*` until: playbook RELEASED **and** explicit confirm in this Cursor chat.

| Agent | Module | Output |
|---|---|---|
| A–E + I | `pipeline/*` | `signals/*` |
| F Supervised | `pipeline/execution.py` | `signals/execution_review.json`, `journal/reviews.jsonl` |
| G Loop | `pipeline/orchestrator.py` | `journal/loop_runs.jsonl` |
| H Unsupervised | Phase 5 | OFF |

## Run
1. Assemble RH MCP dumps into `data/raw/latest_raw.json`
2. `python3 scripts/run_phase2_cycle.py`
3. Review `signals/phase2_summary.json`
