#!/usr/bin/env python3
"""Build a printable HTML + concatenated Python source book of this repo.

Covers every .py module used by Agent F (this Cursor chat) and Agent H
(the autonomous Agentic bot). H's place-permission prompt is not Python
and is listed only as a pointer.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# (path, part, used_by, one-line role)
CATALOG: list[tuple[str, str, str, str]] = [
    ("pipeline/__init__.py", "0 · Package", "F + H", "Pipeline package marker"),
    ("pipeline/io_util.py", "1 · Shared", "F + H", "Paths, rules.json loader, journal helpers"),
    ("pipeline/session.py", "1 · Shared", "F + H", "RTH clock; option entries 09:45–15:45; H lease is on origin/main"),
    ("pipeline/orders.py", "1 · Shared", "F + H", "Working-order states for Robinhood MCP (no open=true)"),
    ("pipeline/quotes.py", "1 · Shared", "F + H", "5s underlying executable price; BOD NLV field extract"),
    ("pipeline/fees.py", "1 · Shared", "F + H", "Dual fee ceilings: 0.49% planned loss and 0.50% with fees"),
    ("pipeline/universe.py", "2 · Agent A", "F + H", "Watchlist extract, crypto drop, inverse-ETF reject, ADV ≥ 2,000,000"),
    ("pipeline/patterns.py", "3 · Agent B", "F + H", "Daily-first H&S / double-triple / triangle; no 1m/3m/5m"),
    ("pipeline/news.py", "4 · Agent C", "F + H", "Factual RH news/earnings pack; no invented sentiment"),
    ("pipeline/options_structure.py", "5 · Agent D", "F + H", "Long call/put; ATM/OTM; 2–3 DTE while overnight off"),
    ("pipeline/equity_day_trade.py", "5 · Agent D", "F only", "Long shares only; inverse-ETF denylist; H has no equity fallback"),
    ("pipeline/greeks.py", "6 · Agent I", "F + H", "Copy RH Greeks only; signed call +0.40–+0.50 / put −0.50–−0.40"),
    ("pipeline/risk.py", "7 · Agent E", "F + H", "Options −20%/+40%; equity −20%/+25%; stop first until OCO"),
    ("pipeline/orchestrator.py", "8 · Agent G", "F + H", "Phase 2 read-only snapshot; h_entry_ready is always false"),
    ("pipeline/execution.py", "9 · Agent F", "F (chat)", "Supervised place-gate: confirm, RTH, 09:45 options, H-owns-RTH"),
    ("scripts/run_phase2_cycle.py", "10 · CLI", "F + H", "Load data/raw/latest_raw.json and run the orchestrator"),
    ("scripts/build_python_source_book.py", "10 · CLI", "docs", "This generator — rebuilds the printable source book"),
    ("pipeline/tests/test_phase2.py", "11 · Tests", "CI / F", "Universe, liquidity, signed delta, ATM/OTM, expiration rank"),
    ("pipeline/tests/test_orders.py", "11 · Tests", "CI / F", "Working states and locked agent_h schema"),
    ("pipeline/tests/test_fees.py", "11 · Tests", "CI / F", "Dual NLV fee ceilings"),
    ("pipeline/tests/test_session.py", "11 · Tests", "CI / F", "ET calendar date and flatten window"),
    ("pipeline/tests/test_equity_day_trade.py", "11 · Tests", "CI / F", "Long-only equity selection and Phase 2 snapshots"),
    ("pipeline/tests/test_execution.py", "11 · Tests", "CI / F", "F place-gate including 09:45 option lock"),
]


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _banner(rel: str, part: str, used_by: str, role: str) -> str:
    line = "=" * 72
    return (
        f"# {line}\n"
        f"# {rel}\n"
        f"# Part: {part}\n"
        f"# Used by: {used_by}\n"
        f"# {role}\n"
        f"# {line}\n\n"
    )


def _catalog() -> list[tuple[str, str, str, str]]:
    return [row for row in CATALOG if (ROOT / row[0]).exists() and _read(row[0]).strip()]


def build_python_book() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    chunks: list[str] = [
        "# ruff: noqa\n",
        "# pylint: skip-file\n",
        '"""PRINTABLE SOURCE BOOK — do not import or execute this file.\n',
        "\n",
        "Agentic trading program: Agent F (supervised Cursor chat) and\n",
        "Agent H (autonomous Agentic bot) share this Python pipeline.\n",
        "Live place_* is Robinhood MCP, not a side effect of this code.\n",
        "H's standing prompt is playbooks/agent_h_autonomous.PROMPT.md (not Python).\n",
        "\n",
        f"Generated: {now}\n",
        "Print companion: docs/agentic-python-source-printable.html\n",
        '"""\n\n',
    ]
    for rel, part, used_by, role in _catalog():
        chunks.append(_banner(rel, part, used_by, role))
        chunks.append(_read(rel).rstrip() + "\n\n")
    return "".join(chunks)


def build_html(py_book: str) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M UTC")
    toc_rows = []
    sections = []
    total_lines = 0
    for rel, part, used_by, role in _catalog():
        src = _read(rel)
        n = src.count("\n") + (0 if src.endswith("\n") or not src else 1)
        total_lines += n
        anchor = rel.replace("/", "-").replace(".", "-")
        toc_rows.append(
            f"<tr><td>{html.escape(part)}</td><td><a href='#{anchor}'>"
            f"<code>{html.escape(rel)}</code></a></td>"
            f"<td>{html.escape(used_by)}</td><td>{n}</td>"
            f"<td>{html.escape(role)}</td></tr>"
        )
        numbered = []
        lines = src.splitlines()
        width = max(3, len(str(len(lines))))
        for i, line in enumerate(lines, 1):
            numbered.append(
                f"<span class='ln'>{i:{width}d}</span> {html.escape(line)}"
            )
        sections.append(
            f"<section class='file' id='{anchor}'>"
            f"<h2>{html.escape(rel)}</h2>"
            f"<p class='meta'><strong>{html.escape(part)}</strong> · {html.escape(used_by)}"
            f" · {n} lines · {html.escape(role)}</p>"
            f"<pre class='source'>{chr(10).join(numbered)}\n</pre>"
            f"</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Agentic Python Source Book (Printable)</title>
  <style>
    :root {{ --ink:#111; --muted:#333; --line:#222; --bg:#fff; --box:#f4f4f4; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; color: var(--ink); background: var(--bg);
      font-family: "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 10.4pt; line-height: 1.35;
    }}
    .toolbar {{
      position: sticky; top: 0; z-index: 20; display: flex; gap: 12px;
      align-items: center; background: #111; color: #fff;
      padding: 10px 16px; font-size: 13px;
    }}
    .toolbar button {{
      background: #fff; color: #111; border: 0; padding: 8px 14px;
      font-weight: 700; cursor: pointer;
    }}
    .page {{ max-width: 8.5in; margin: 0 auto; padding: 0.5in 0.55in 0.65in; }}
    h1 {{ font-size: 20pt; margin: 0 0 0.08in; letter-spacing: -0.02em; }}
    h2 {{
      font-size: 12pt; margin: 0.28in 0 0.08in; padding-bottom: 0.04in;
      border-bottom: 1.5pt solid var(--line); page-break-after: avoid;
    }}
    h3 {{ font-size: 11pt; margin: 0.16in 0 0.06in; page-break-after: avoid; }}
    .kicker {{ font-size: 9.5pt; letter-spacing: 0.08em; text-transform: uppercase; }}
    .rule {{ width: 1.3in; height: 3px; background: #111; margin: 0.12in 0 0.18in; }}
    .meta, .note, .footer {{ font-size: 9.3pt; color: var(--muted); }}
    .meta strong {{ color: var(--ink); }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0.1in 0 0.16in; }}
    .badge {{
      border: 1pt solid var(--line); padding: 3px 8px; font-size: 8.4pt; background: var(--box);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 8.8pt; margin: 0 0 0.14in; }}
    th, td {{ border: 1pt solid var(--line); padding: 0.045in 0.06in; vertical-align: top; text-align: left; }}
    th {{ background: #e8e8e8; font-weight: 700; }}
    .card {{
      border: 1pt solid var(--line); padding: 0.1in 0.12in; background: var(--box);
      page-break-inside: avoid; margin-bottom: 0.1in;
    }}
    ul {{ margin: 0.04in 0 0.08in; padding-left: 0.2in; }}
    li {{ margin: 0.03in 0; }}
    code {{ font-family: "IBM Plex Mono", Consolas, "Courier New", monospace; font-size: 8.8pt; }}
    pre.source {{
      font-family: "IBM Plex Mono", Consolas, "Courier New", monospace;
      font-size: 7.15pt; line-height: 1.28; white-space: pre-wrap; word-break: break-word;
      background: var(--box); border: 1pt solid var(--line); padding: 0.09in 0.1in;
      margin: 0 0 0.08in;
    }}
    pre.source .ln {{ color: #888; margin-right: 0.12in; user-select: none; }}
    .file {{ page-break-before: always; }}
    .footer {{ margin-top: 0.18in; padding-top: 0.08in; border-top: 1pt solid #999; font-size: 8.2pt; }}
    @media print {{
      .no-print {{ display: none !important; }}
      .page {{ max-width: none; padding: 0; }}
      a {{ color: inherit; text-decoration: none; }}
      h2, table, .card {{ break-inside: avoid; }}
      pre.source {{ font-size: 7pt; }}
    }}
    @page {{ size: Letter portrait; margin: 0.45in; }}
  </style>
</head>
<body>
  <div class="toolbar no-print">
    <button type="button" onclick="window.print()">Print / Save as PDF</button>
    <span>Agentic Python source — Letter portrait · {total_lines} lines · {len(CATALOG)} files</span>
  </div>
  <div class="page">
    <p class="kicker">Jarrod Besner · Agentic ••••2907</p>
    <h1>Python source book</h1>
    <div class="rule"></div>
    <p class="meta">Chat agent <strong>F</strong> and autonomous bot <strong>H</strong> share this pipeline.
    Generated {html.escape(now)}. Companion file: <code>docs/agentic_python_source_book.py</code>.</p>
    <div class="badge-row">
      <span class="badge">{len(CATALOG)} Python files</span>
      <span class="badge">{total_lines} lines</span>
      <span class="badge">Language: Python 3</span>
      <span class="badge">Does not place orders</span>
    </div>

    <h3>Who uses which code</h3>
    <div class="card">
      <ul>
        <li><strong>Agent F (this Cursor chat)</strong> — supervised. Reads the pipeline, reviews tickets via
            <code>pipeline/execution.py</code>, and only calls Robinhood <code>place_*</code> after an explicit
            confirm of a specific order. Blocked during RTH while H is enabled.</li>
        <li><strong>Agent H (Agentic AI Bot)</strong> — unsupervised Cursor Automation. The standing prompt is
            <code>playbooks/agent_h_autonomous.PROMPT.md</code> (markdown, not Python). On each fire H checks out
            <code>main</code>, reads <code>config/rules.json</code> → <code>agent_h</code>, and uses
            daily → 1-hour → completed 10-minute → live quote only (no 1m / 3m / 5m).
            Live <code>place_*</code> is Robinhood MCP from that prompt, not a pipeline side effect.
            H is options-only; it must ignore equity candidates.</li>
        <li><strong>Not in this book:</strong> lock JSON, playbooks, and the H prompt. Those are not Python.</li>
      </ul>
    </div>

    <h3>Contents</h3>
    <table>
      <thead><tr><th>Part</th><th>File</th><th>Used by</th><th>Lines</th><th>Role</th></tr></thead>
      <tbody>
        {''.join(toc_rows)}
      </tbody>
    </table>
    <p class="note">Each file starts on a new printed page. Source is verbatim Python from the repo.</p>
    {''.join(sections)}
    <p class="footer">Agentic Python source book · {html.escape(now)} · {total_lines} lines in {len(CATALOG)} files ·
    print from this HTML or open <code>docs/agentic_python_source_book.py</code>.</p>
  </div>
</body>
</html>
"""


def build_pdf(path: Path) -> None:
    import pymupdf

    page_w, page_h = 612, 792
    margin = 36
    body_font = 7.2
    header_font = 9.5
    cover_title = 22
    line_h = 9.4
    usable_h = page_h - margin * 2 - 18
    max_lines = int(usable_h / line_h)
    max_chars = 108

    doc = pymupdf.open()
    now = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M UTC")

    def new_page():
        return doc.new_page(width=page_w, height=page_h)

    def footer(page, label: str) -> None:
        page.insert_text(
            pymupdf.Point(margin, page_h - 18),
            f"Agentic Python source  ·  {label}  ·  {now}  ·  page {page.number + 1}",
            fontname="helv",
            fontsize=7,
            color=(0.25, 0.25, 0.25),
        )

    def wrap(text: str, width: int) -> list[str]:
        if len(text) <= width:
            return [text]
        words = text.replace("\t", "    ").split(" ")
        lines: list[str] = []
        cur = ""
        for word in words:
            trial = word if not cur else f"{cur} {word}"
            if len(trial) <= width:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            while len(word) > width:
                lines.append(word[:width])
                word = word[width:]
            cur = word
        if cur:
            lines.append(cur)
        return lines or [""]

    # Cover
    page = new_page()
    y = 72
    page.insert_text(pymupdf.Point(margin, y), "JARROD BESNER  ·  AGENTIC", fontname="helv", fontsize=10)
    y += 36
    page.insert_text(pymupdf.Point(margin, y), "Python source book", fontname="helv", fontsize=cover_title)
    y += 28
    page.draw_rect(pymupdf.Rect(margin, y, margin + 90, y + 3), fill=(0, 0, 0), width=0)
    y += 28
    cover_lines = [
        "All Python used by Agent F (supervised Cursor chat) and Agent H",
        "(autonomous Agentic bot). Live place_* is Robinhood MCP, not a",
        "side effect of this code. H's standing prompt is markdown:",
        "playbooks/agent_h_autonomous.PROMPT.md — not included here.",
        "",
        f"{len(CATALOG)} files  ·  generated {now}",
        "Language: Python 3  ·  Letter portrait",
    ]
    for line in cover_lines:
        page.insert_text(pymupdf.Point(margin, y), line, fontname="helv", fontsize=11)
        y += 16
    y += 10
    page.insert_text(pymupdf.Point(margin, y), "Contents", fontname="helv", fontsize=13)
    y += 18
    for rel, part, used_by, role in _catalog():
        n = _read(rel).count("\n") + 1
        row = f"{part:16s}  {rel:42s}  {used_by:10s}  {n:4d}  {role}"
        for w in wrap(row, 98):
            if y > page_h - 48:
                footer(page, "cover")
                page = new_page()
                y = margin + 12
            page.insert_text(pymupdf.Point(margin, y), w, fontname="cour", fontsize=7)
            y += 10
    footer(page, "cover")

    for rel, part, used_by, role in _catalog():
        src_lines = _read(rel).splitlines()
        page = new_page()
        header = f"{rel}   ·   {part}   ·   {used_by}   ·   {role}"
        page.insert_text(pymupdf.Point(margin, margin + 4), header[:110], fontname="helv", fontsize=header_font)
        y = margin + 18
        page.draw_line(pymupdf.Point(margin, y), pymupdf.Point(page_w - margin, y), color=(0, 0, 0), width=0.8)
        y += 12
        used = 0
        width = max(3, len(str(len(src_lines))))
        for i, raw in enumerate(src_lines, 1):
            prefix = f"{i:{width}d}  "
            wrapped = wrap(raw.replace("\t", "    "), max_chars - len(prefix)) or [""]
            for j, chunk in enumerate(wrapped):
                if used >= max_lines:
                    footer(page, rel)
                    page = new_page()
                    page.insert_text(
                        pymupdf.Point(margin, margin + 4),
                        f"{rel}  (continued)",
                        fontname="helv",
                        fontsize=header_font,
                    )
                    y = margin + 18
                    page.draw_line(
                        pymupdf.Point(margin, y),
                        pymupdf.Point(page_w - margin, y),
                        color=(0, 0, 0),
                        width=0.8,
                    )
                    y += 12
                    used = 0
                line = prefix + chunk if j == 0 else (" " * len(prefix)) + chunk
                page.insert_text(pymupdf.Point(margin, y), line, fontname="cour", fontsize=body_font)
                y += line_h
                used += 1
        footer(page, rel)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    py_book = build_python_book()
    html_doc = build_html(py_book)
    py_path = DOCS / "agentic_python_source_book.py"
    html_path = DOCS / "agentic-python-source-printable.html"
    py_path.write_text(py_book, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"wrote {py_path} ({py_path.stat().st_size} bytes)")
    print(f"wrote {html_path} ({html_path.stat().st_size} bytes)")
    pdf_candidates = [Path("/dev/shm/agentic-python-source.pdf"), DOCS / "agentic-python-source.pdf"]
    pdf_path = pdf_candidates[0]
    try:
        build_pdf(pdf_path)
        print(f"wrote {pdf_path} ({pdf_path.stat().st_size} bytes)")
        dest = DOCS / "agentic-python-source.pdf"
        if pdf_path != dest:
            dest.write_bytes(pdf_path.read_bytes())
            print(f"copied {dest} ({dest.stat().st_size} bytes)")
    except OSError as exc:
        print(f"pdf write skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
