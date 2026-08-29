#!/usr/bin/env python3
"""Batch-run the baseline and the advanced agent over eval/bugs/bug_01..bug_13.

For every bug this launches two subprocesses, each with its own timeout:

    python baseline/run_baseline.py eval/bugs/<bug>
    python advanced/run_agent.py   eval/bugs/<bug>

captures their stdout, parses out (resolved, iterations, wall-clock), and then
prints a side-by-side table and writes eval/results/summary.json and
eval/results/summary.md (a markdown table ready to paste into the README).

Failure handling: a run that crashes, times out, or produces output we cannot
parse is recorded as "timeout"/"error" for that one cell only. The batch always
continues to the next run.

Usage:
    python eval/run_all.py                     # all ten bugs, both systems
    python eval/run_all.py --timeout 180       # override per-run timeout (s)
    python eval/run_all.py --bugs bug_03 bug_07
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Force UTF-8 on the standard streams so table/markdown output containing →, —,
# ·, ≈ never crashes when stdout/stderr is a pipe on a non-UTF-8 locale (cp1252
# on Windows). Same fix as run_baseline.py / run_agent.py.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "eval" / "results"
BUGS_DIR = REPO_ROOT / "eval" / "bugs"

BASELINE_SCRIPT = REPO_ROOT / "baseline" / "run_baseline.py"
ADVANCED_SCRIPT = REPO_ROOT / "advanced" / "run_agent.py"

DEFAULT_TIMEOUT_S = 240
DEFAULT_BUGS = [f"bug_{i:02d}" for i in range(1, 14)]


# --------------------------------------------------------------------------- #
# stdout parsing — one parser per system
# --------------------------------------------------------------------------- #
def _find(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1) if m else None


def parse_baseline(stdout: str) -> dict[str, Any]:
    """Pull the verdict out of baseline/run_baseline.py stdout."""
    fixed = _find(r"^bug fixed \(.*\):\s*(True|False)\s*$", stdout)
    wall = _find(r"^total wall-clock time:\s*([\d.]+)s", stdout)
    if fixed is None:
        raise ValueError("no 'bug fixed (...)' line in baseline output")
    return {
        "resolved": fixed == "True",
        "iterations": 1,  # baseline is always a single shot
        "wall_clock_seconds": float(wall) if wall else None,
    }


def parse_advanced(stdout: str) -> dict[str, Any]:
    """Pull the verdict out of advanced/run_agent.py stdout."""
    resolved = _find(r"^resolved:\s*(True|False)", stdout)
    iters = _find(r"^iterations used:\s*(\d+)\s*/", stdout)
    wall = _find(r"^wall-clock time:\s*([\d.]+)s", stdout)
    if resolved is None:
        raise ValueError("no 'resolved:' line in advanced output")
    return {
        "resolved": resolved == "True",
        "iterations": int(iters) if iters else None,
        "wall_clock_seconds": float(wall) if wall else None,
    }


# --------------------------------------------------------------------------- #
# subprocess runner
# --------------------------------------------------------------------------- #
def run_one(
    script: Path,
    bug_rel: str,
    timeout_s: int,
    parser: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    """Run one (system, bug) subprocess; always returns a normalised dict.

    status is one of: "resolved", "unresolved", "timeout", "error".
    """
    cmd = [sys.executable, str(script), bug_rel]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            env=os.environ,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "resolved": None,
            "iterations": None,
            "wall_clock_seconds": round(time.perf_counter() - started, 1),
            "error": f"timed out after {timeout_s}s",
        }
    except Exception as exc:  # launch failure, etc. — never abort the batch
        return {
            "status": "error",
            "resolved": None,
            "iterations": None,
            "wall_clock_seconds": round(time.perf_counter() - started, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }

    elapsed = round(time.perf_counter() - started, 1)
    try:
        parsed = parser(proc.stdout)
    except Exception as exc:
        return {
            "status": "error",
            "resolved": None,
            "iterations": None,
            "wall_clock_seconds": elapsed,
            "exit_code": proc.returncode,
            "error": f"could not parse output ({exc})",
            "stdout_tail": proc.stdout[-1000:],
            "stderr_tail": proc.stderr[-1000:],
        }

    if parsed.get("wall_clock_seconds") is None:
        parsed["wall_clock_seconds"] = elapsed  # fall back to our own timing
    parsed["status"] = "resolved" if parsed["resolved"] else "unresolved"
    parsed["exit_code"] = proc.returncode
    return parsed


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def cell(res: dict[str, Any], show_iters: bool) -> str:
    """One table cell, e.g. 'PASS 40.6s (5it)', 'FAIL 12.3s', 'TIMEOUT'."""
    status = res["status"]
    if status == "timeout":
        return "TIMEOUT"
    if status == "error":
        return "ERROR"
    mark = "PASS" if res["resolved"] else "FAIL"
    wall = res.get("wall_clock_seconds")
    txt = f"{mark} {wall:g}s" if wall is not None else mark
    if show_iters and res.get("iterations") is not None:
        txt += f" ({res['iterations']}it)"
    return txt


def render_rows(bugs: list[dict[str, Any]]) -> tuple[list[tuple[str, str, str]], tuple[str, str, str]]:
    rows = [
        (
            b["bug_id"],
            cell(b["baseline"], show_iters=False),
            cell(b["advanced"], show_iters=True),
        )
        for b in bugs
    ]
    n = len(bugs)
    b_ok = sum(1 for b in bugs if b["baseline"]["status"] == "resolved")
    a_ok = sum(1 for b in bugs if b["advanced"]["status"] == "resolved")
    totals = ("Total", f"{b_ok}/{n} resolved", f"{a_ok}/{n} resolved")
    return rows, totals


def print_table(rows: list[tuple[str, str, str]], totals: tuple[str, str, str]) -> None:
    header = ("bug", "baseline", "advanced")
    all_rows = [header, *rows, totals]
    w = [max(len(r[i]) for r in all_rows) for i in range(3)]

    def fmt(r: tuple[str, str, str]) -> str:
        return f"  {r[0]:<{w[0]}}   {r[1]:<{w[1]}}   {r[2]:<{w[2]}}"

    sep = "  " + "-" * (w[0] + w[1] + w[2] + 6)
    print(fmt(header))
    print(sep)
    for r in rows:
        print(fmt(r))
    print(sep)
    print(fmt(totals))


def build_markdown(
    rows: list[tuple[str, str, str]],
    totals: tuple[str, str, str],
    generated_at: str,
    timeout_s: int,
) -> str:
    lines = [
        "# Eval summary",
        "",
        f"_Generated {generated_at} · per-run timeout {timeout_s}s · "
        "cell format: `PASS/FAIL <wall-clock> (<iterations>)`; "
        "`ERROR` = crashed or unparseable, `TIMEOUT` = exceeded the per-run limit._",
        "",
        "| Bug | Baseline | Advanced |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {b} | {bl} | {ad} |" for b, bl, ad in rows]
    lines.append(f"| **{totals[0]}** | **{totals[1]}** | **{totals[2]}** |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                    help=f"per-run timeout in seconds (default {DEFAULT_TIMEOUT_S})")
    ap.add_argument("--bugs", nargs="+", default=DEFAULT_BUGS,
                    help="bug ids to run (default: bug_01 .. bug_13)")
    ap.add_argument("--no-merge", action="store_true",
                    help="overwrite summary.json/.md with only this run's bugs "
                         "instead of merging into the existing results")
    args = ap.parse_args()

    for script in (BASELINE_SCRIPT, ADVANCED_SCRIPT):
        if not script.is_file():
            print(f"error: {script} not found", file=sys.stderr)
            return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    batch_start = time.perf_counter()

    bugs: list[dict[str, Any]] = []
    for i, bug_id in enumerate(args.bugs, 1):
        bug_rel = f"eval/bugs/{bug_id}"
        bug_dir = BUGS_DIR / bug_id
        print(f"[{i}/{len(args.bugs)}] {bug_id}", file=sys.stderr, flush=True)

        if not (bug_dir / "repo").is_dir() or not (bug_dir / "bug_report.md").is_file():
            missing = {
                "status": "error",
                "resolved": None,
                "iterations": None,
                "wall_clock_seconds": None,
                "error": f"{bug_rel} is missing repo/ or bug_report.md",
            }
            bugs.append({"bug_id": bug_id, "baseline": dict(missing), "advanced": dict(missing)})
            print("      skipped (bug directory incomplete)", file=sys.stderr, flush=True)
            continue

        print("      baseline ...", end="", file=sys.stderr, flush=True)
        baseline = run_one(BASELINE_SCRIPT, bug_rel, args.timeout, parse_baseline)
        print(f" {baseline['status']}", file=sys.stderr, flush=True)

        print("      advanced ...", end="", file=sys.stderr, flush=True)
        advanced = run_one(ADVANCED_SCRIPT, bug_rel, args.timeout, parse_advanced)
        print(f" {advanced['status']}", file=sys.stderr, flush=True)

        bugs.append({"bug_id": bug_id, "baseline": baseline, "advanced": advanced})

    ran_ids = {b["bug_id"] for b in bugs}
    carried = 0
    summary_path = RESULTS_DIR / "summary.json"
    if not args.no_merge and summary_path.is_file():
        try:
            prior = json.loads(summary_path.read_text(encoding="utf-8")).get("bugs", [])
        except (json.JSONDecodeError, OSError):
            prior = []
        for b in prior:
            if b.get("bug_id") and b["bug_id"] not in ran_ids:
                bugs.append(b)
                carried += 1

    bugs.sort(key=lambda b: b["bug_id"])

    rows, totals = render_rows(bugs)
    n = len(bugs)
    b_ok = sum(1 for b in bugs if b["baseline"]["status"] == "resolved")
    a_ok = sum(1 for b in bugs if b["advanced"]["status"] == "resolved")

    summary = {
        "generated_at": generated_at,
        "timeout_seconds": args.timeout,
        "batch_wall_clock_seconds": round(time.perf_counter() - batch_start, 1),
        "ran_this_batch": sorted(ran_ids),
        "carried_from_prior_summary": carried,
        "bugs": bugs,
        "totals": {"count": n, "baseline_resolved": b_ok, "advanced_resolved": a_ok},
    }

    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "summary.md").write_text(
        build_markdown(rows, totals, generated_at, args.timeout), encoding="utf-8"
    )

    print()
    print_table(rows, totals)
    print()
    print(f"baseline: {b_ok}/{n} resolved   advanced: {a_ok}/{n} resolved")
    if carried:
        print(f"(ran {len(ran_ids)} this batch, carried {carried} from the previous summary)")
    print(f"wrote {RESULTS_DIR / 'summary.json'}")
    print(f"wrote {RESULTS_DIR / 'summary.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
