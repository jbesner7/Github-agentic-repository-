# Agents (Phase 3)

Phase 2 remains the signal pipeline. Phase 3 adds **Agent F** dry review.

Options playbook is **RELEASED**. **No** `place_*` until an explicit confirm of a **specific** order in this Cursor chat.

| Agent | Module | Output |
|---|---|---|
| A–E + I | `pipeline/*` | `signals/*` |
| F Supervised | `pipeline/execution.py` | `signals/execution_review.json`, `journal/reviews.jsonl` |
| G Loop | `pipeline/orchestrator.py` | `journal/loop_runs.jsonl` |
| H Unsupervised | `playbooks/agent_h_autonomous.PROMPT.md` | OFF until you paste + activate a Cursor Automation |

## Run
1. Assemble RH MCP dumps into `data/raw/latest_raw.json`
2. `python3 scripts/run_phase2_cycle.py`
3. Review `signals/phase2_summary.json`
