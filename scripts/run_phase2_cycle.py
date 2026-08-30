#!/usr/bin/env python3
"""Run Phase 2 pipeline from a raw MCP dump JSON file (read-only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.io_util import DATA_RAW
from pipeline.orchestrator import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 read-only signal pipeline")
    parser.add_argument(
        "--raw",
        type=Path,
        default=DATA_RAW / "latest_raw.json",
        help="Path to RH MCP assembled raw JSON",
    )
    args = parser.parse_args()
    if not args.raw.exists():
        print(f"Raw file not found: {args.raw}", file=sys.stderr)
        return 1
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    summary = run_pipeline(raw)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
