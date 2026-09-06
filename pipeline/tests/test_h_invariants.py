from pathlib import Path

from pipeline.h_invariants import compare_prompt_to_rules, compare_rules_to_expected
from pipeline.io_util import load_rules


def test_rules_and_prompt_share_numeric_invariants():
    rules = load_rules()
    agent_h = rules["agent_h"]
    assert compare_rules_to_expected(agent_h) == []
    prompt = (Path(__file__).resolve().parents[2] / "playbooks" / "agent_h_autonomous.PROMPT.md").read_text()
    assert compare_prompt_to_rules(prompt, agent_h) == []


def test_invariant_checker_flags_a_drifted_number():
    rules = load_rules()
    drifted = dict(rules["agent_h"])
    drifted["no_new_entries_after"] = "15:30"
    mismatches = compare_rules_to_expected(drifted)
    assert any(item.startswith("no_new_entries_after") for item in mismatches)
