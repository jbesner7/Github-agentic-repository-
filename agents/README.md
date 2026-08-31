# Agents

Phase 2 is the signal pipeline. Live `place_*` is **not** a pipeline side effect.

| Agent | Module | Output |
|---|---|---|
| A–E + I | `pipeline/*` | `signals/*` (snapshots; do not place from git copies) |
| F Supervised | `pipeline/execution.py` | Dry review until a specific-order confirm. Blocked during RTH while H is enabled. |
| G Loop | `pipeline/orchestrator.py` | One-shot cycle, not a daemon. `journal/loop_runs.jsonl` |
| H Unsupervised | `playbooks/agent_h_autonomous.PROMPT.md` | **ON** — Automation [Agentic AI Bot](https://cursor.com/automations/9af478e7-a454-11f1-a7d1-d6b4613131ce). Disable there to stop. Re-paste the prompt after edits. |

Options and equities playbooks are **RELEASED**. This chat still needs an explicit confirm of a **specific** order.

## Run

1. Assemble RH MCP dumps into `data/raw/latest_raw.json`
2. `python3 scripts/run_phase2_cycle.py`
3. Review `signals/phase2_summary.json`
