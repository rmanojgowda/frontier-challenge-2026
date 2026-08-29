#!/usr/bin/env python3
"""Evidence-driven automated debugging agent (the judged submission).

Given a bug directory with the same layout as the baseline
(``bug_report.md`` + ``repo/``), the agent works inside a throwaway sandbox
copy of ``repo/`` and autonomously:

    investigate -> reproduce the failure -> locate the root cause ->
    patch it -> verify the fix resolves the report without regressions

Every step (the model's reasoning, the tool it called, the input, the result,
a timestamp) is appended to ``eval/results/<bug_id>_trajectory.json`` so the
output is a *chain of evidence*, not just a diff.

The original ``eval/bugs/`` tree is never modified — all file writes and test
runs happen in ``tempfile.mkdtemp()``.

Usage:
    python advanced/run_agent.py eval/bugs/bug_01

Requires ANTHROPIC_API_KEY in the environment and ``anthropic`` + ``pytest``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

# Force UTF-8 on the standard streams so printing the model's root-cause summary
# (which routinely contains →, —, π, …) never crashes when stdout/stderr is a
# pipe on a non-UTF-8 locale (e.g. cp1252 on Windows).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000
MAX_TOOL_CALLS = 15
TEST_TIMEOUT_S = 30

RESULT_LINE_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR)\b")
TEST_FILE_RE = re.compile(r"(^test_.*\.py$)|(.*_test\.py$)|(^conftest\.py$)")
MAX_TOOL_RESULT_CHARS = 6000      # cap on what is fed back to the model / stored verbose
MAX_RESULT_SUMMARY_CHARS = 700    # cap on the readable per-step result summary
MAX_DECISION_CHARS = 240          # cap on the one-line decision string


# --------------------------------------------------------------------------- #
# Sandbox + pytest helpers
# --------------------------------------------------------------------------- #
def make_sandbox(src_repo: Path) -> Path:
    """Copy ``src_repo`` into a fresh temp dir and return the copy's path."""
    sandbox = Path(tempfile.mkdtemp(prefix="agent_sandbox_")) / "repo"
    shutil.copytree(
        src_repo, sandbox,
        ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", "*.pyc", ".git", ".mypy_cache",
            ".ruff_cache",
        ),
    )
    return sandbox


def collect_test_files(sandbox: Path) -> set[Path]:
    """Resolved paths of every test file present in the sandbox right now."""
    return {
        p.resolve()
        for p in sandbox.rglob("*.py")
        if TEST_FILE_RE.match(p.name)
    }


def safe_path(sandbox: Path, rel: str) -> Path:
    """Resolve ``rel`` inside the sandbox, refusing any path that escapes it."""
    target = (sandbox / rel).resolve()
    if sandbox.resolve() not in target.parents and target != sandbox.resolve():
        raise ValueError(f"path {rel!r} escapes the sandbox")
    return target


def _pytest_node(sandbox: Path, target: str | None) -> str:
    """Turn an optional pytest target into a concrete node argument."""
    if not target:
        return str(sandbox)
    if "::" in target:  # 'file.py::test_name' node id — keep as-is under sandbox
        file_part, _, rest = target.partition("::")
        return f"{safe_path(sandbox, file_part)}::{rest}"
    return str(safe_path(sandbox, target))


def run_pytest(sandbox: Path, target: str | None = None) -> dict[str, Any]:
    """Run pytest in the sandbox; return structured + raw results."""
    cmd = [sys.executable, "-m", "pytest", _pytest_node(sandbox, target),
           "-v", "--tb=short", "-p", "no:cacheprovider"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TEST_TIMEOUT_S,
        )
        stdout, stderr, timed_out = proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        timed_out = True

    outcomes: dict[str, str] = {}
    for line in stdout.splitlines():
        m = RESULT_LINE_RE.match(line.strip())
        if m:
            outcomes[m.group(1)] = m.group(2)

    summary = ""
    for line in reversed(stdout.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            summary = line.strip().strip("=").strip()
            break

    return {
        "outcomes": outcomes,
        "summary": summary,
        "timed_out": timed_out,
        "raw": (stdout + ("\n" + stderr if stderr else "")).strip(),
    }


# --------------------------------------------------------------------------- #
# Tool implementations (operate only on the sandbox)
# --------------------------------------------------------------------------- #
class Tools:
    def __init__(self, sandbox: Path, protected_test_files: set[Path] | None = None):
        self.sandbox = sandbox
        self.last_full_run: dict[str, Any] | None = None
        # test files that existed at setup — the agent may add NEW test files
        # (its regression test) but may not overwrite these.
        self.protected_test_files: set[Path] = protected_test_files or set()

    def list_files(self, directory: str = ".") -> str:
        base = safe_path(self.sandbox, directory)
        if not base.is_dir():
            return f"error: {directory!r} is not a directory"
        entries = []
        for p in sorted(base.rglob("*")):
            if p.is_file():
                entries.append(p.relative_to(self.sandbox).as_posix())
        return "\n".join(entries) or "(empty)"

    def read_file(self, path: str) -> str:
        target = safe_path(self.sandbox, path)
        if not target.is_file():
            return f"error: {path!r} not found"
        text = target.read_text(encoding="utf-8", errors="replace")
        numbered = "\n".join(
            f"{i:4d}  {line}" for i, line in enumerate(text.splitlines(), 1)
        )
        return numbered or "(empty file)"

    def search_code(self, pattern: str) -> str:
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return f"error: invalid regex: {exc}"
        hits = []
        for p in sorted(self.sandbox.rglob("*.py")):
            for i, line in enumerate(
                p.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if rx.search(line):
                    rel = p.relative_to(self.sandbox).as_posix()
                    hits.append(f"{rel}:{i}: {line.strip()}")
                    if len(hits) >= 100:
                        return "\n".join(hits) + "\n... (truncated at 100 hits)"
        return "\n".join(hits) or "(no matches)"

    def run_tests(self, test_path: str | None = None) -> str:
        result = run_pytest(self.sandbox, test_path)
        if test_path is None:
            self.last_full_run = result
        header = "TIMED OUT after %ds\n" % TEST_TIMEOUT_S if result["timed_out"] else ""
        return header + result["raw"]

    def apply_patch(self, file_path: str, new_content: str) -> str:
        # Guard 1: the write must resolve inside the sandbox root — safe_path()
        # raises otherwise. The original eval/bugs/ tree is never a write
        # target: every tool operates on the temp-dir copy.
        target = safe_path(self.sandbox, file_path)
        # Guard 2: pre-existing test files are read-only. New test files (the
        # agent's own regression test) are fine.
        if target.resolve() in self.protected_test_files:
            rel = target.resolve().relative_to(self.sandbox.resolve()).as_posix()
            return (
                f"refused: {rel!r} is a protected original test file that existed "
                "at setup — it must not be modified. You may create a NEW test "
                "file (e.g. test_regression.py) to reproduce the bug instead. "
                "(This is a protection rule, not a sandbox-escape error.)"
            )
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.is_file()
        target.write_text(new_content, encoding="utf-8")
        verb = "updated" if existed else "created"
        # automatic checkpoint: full suite re-run
        checkpoint = run_pytest(self.sandbox, None)
        self.last_full_run = checkpoint
        return json.dumps({
            "patch": f"{verb} {file_path}",
            "checkpoint_summary": checkpoint["summary"],
            "checkpoint_outcomes": checkpoint["outcomes"],
            "checkpoint_timed_out": checkpoint["timed_out"],
            "checkpoint_raw_tail": "\n".join(checkpoint["raw"].splitlines()[-40:]),
        }, indent=2)


TOOL_SCHEMAS = [
    {
        "name": "list_files",
        "description": "List every file in the repository sandbox (recursive). "
                       "Optionally scope to a subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string",
                              "description": "subdirectory to list; defaults to the repo root"},
            },
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the sandbox. Returns the contents with line numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "path relative to the repo root"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": "Regex search across every .py file in the sandbox. "
                       "Returns file:line: matched-line for each hit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Python regular expression"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run pytest inside the sandbox and return the captured output. "
                       "Pass test_path (a file or a 'file::test' node id) to run a subset, "
                       "or omit it to run the whole suite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "test_path": {"type": "string",
                              "description": "optional pytest target, e.g. "
                                             "'test_stringutils.py::test_truncate_longer_than_limit'"},
            },
            "required": [],
        },
    },
    {
        "name": "apply_patch",
        "description": "Write new_content (the COMPLETE file) to a path inside the sandbox. "
                       "You MAY create or modify test files here (e.g. to add a regression "
                       "test that reproduces the bug) as well as source files. After writing, "
                       "the full test suite is automatically re-run and returned as a checkpoint.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "path relative to the repo root"},
                "new_content": {"type": "string", "description": "the entire new file contents"},
            },
            "required": ["file_path", "new_content"],
        },
    },
]

SYSTEM_PROMPT = """\
You are an evidence-driven debugging agent. You are given a user-filed bug \
report and a sandboxed copy of a small Python repository. Your job is to \
produce a *chain of evidence* that leads to a verified fix:

1. Investigate the codebase (list_files, read_file, search_code).
2. Reproduce the reported failure by running the tests. Confirm you can see \
   the exact symptom from the bug report before theorising.
3. Identify the single root cause. State it explicitly, with the file and line.
4. Apply the smallest patch that fixes the root cause (apply_patch). Do not \
   patch around symptoms. Do not edit tests.
5. Verify: after your patch, the previously-failing test(s) must pass and no \
   previously-passing test may regress. The automatic checkpoint after each \
   apply_patch shows you the full-suite result.

Work in small, deliberate steps and explain your reasoning before each tool \
call. When the fix is verified, stop calling tools and reply with a concise \
final report containing: the root cause (file/line/why), the fix you made, and \
the evidence that it works (which tests went from failing to passing, and that \
nothing regressed). If you cannot fix it within the tool budget, say so and \
report your best understanding of the root cause.
"""


# --------------------------------------------------------------------------- #
# Trajectory logging
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(text: str, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... (truncated, {len(text) - limit} more chars)"


def extract_decision(assistant_text: str) -> str:
    """One line summarising *why* the agent took this action.

    Uses the last non-empty line of the model's reasoning (that line is
    typically the "so I'll do X" conclusion), collapsed and capped.
    """
    lines = [ln.strip() for ln in assistant_text.splitlines() if ln.strip()]
    if not lines:
        return "(no stated reasoning)"
    chosen = lines[-1]
    # a trailing question or heading is rarely the real rationale; prefer the
    # previous line in that case
    if len(lines) > 1 and (chosen.endswith(":") or chosen.endswith("?")):
        chosen = lines[-2]
    chosen = " ".join(chosen.split())
    if len(chosen) > MAX_DECISION_CHARS:
        chosen = chosen[:MAX_DECISION_CHARS].rstrip() + "…"
    return chosen


_TEST_VERDICT_KEYS = ("PASSED", "FAILED", "ERROR", "assert")


def summarize_result(
    text: str,
    limit: int = MAX_RESULT_SUMMARY_CHARS,
    is_test_output: bool = False,
) -> str:
    """A short, readable digest of a tool result — not the full stdout dump.

    For ``run_tests`` output, verdict lines (PASSED / FAILED / ERROR / assert)
    are pulled out first, in original order, up to 10; any remaining slots are
    filled with the leading lines so the summary still has context. Otherwise
    it's a plain head-truncation.
    """
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]

    if is_test_output:
        selected = [ln for ln in lines if any(k in ln for k in _TEST_VERDICT_KEYS)][:10]
        if len(selected) < 10:
            for ln in lines:  # pad with leading context lines, no duplicates
                if ln not in selected:
                    selected.append(ln)
                    if len(selected) >= 10:
                        break
    else:
        selected = lines[:10]

    digest = "\n".join(selected)
    if len(digest) > limit:
        digest = digest[:limit].rstrip() + " …"
    omitted = len(lines) - len(selected)
    if omitted > 0:
        digest += f"\n… (+{omitted} more lines; see verbose.tool_result_raw)"
    return digest or "(empty result)"


# --------------------------------------------------------------------------- #
# Agent loop
# --------------------------------------------------------------------------- #
def run_agent(bug_dir: Path) -> dict[str, Any]:
    wall_start = time.perf_counter()

    bug_id = bug_dir.name
    src_repo = bug_dir / "repo"
    report = (bug_dir / "bug_report.md").read_text(encoding="utf-8")

    sandbox = make_sandbox(src_repo)
    # Snapshot the test files that exist BEFORE the agent runs — apply_patch
    # will refuse to overwrite any of these (but allows brand-new test files).
    original_test_files = collect_test_files(sandbox)
    tools = Tools(sandbox, protected_test_files=original_test_files)

    # Baseline snapshot (for the final verdict only — the agent still reproduces
    # the failure itself as part of its evidence chain).
    baseline = run_pytest(sandbox, None)
    originally_failing = {t for t, r in baseline["outcomes"].items() if r != "PASSED"}
    originally_passing = {t for t, r in baseline["outcomes"].items() if r == "PASSED"}

    trajectory: list[dict[str, Any]] = [{
        "step": 0,
        "timestamp": now_iso(),
        "event": "setup",
        "sandbox": str(sandbox),
        "baseline_summary": baseline["summary"],
        "originally_failing": sorted(originally_failing),
        "originally_passing": sorted(originally_passing),
        "protected_test_files": sorted(
            p.relative_to(sandbox.resolve()).as_posix() for p in original_test_files
        ),
    }]

    client = anthropic.Anthropic()
    user_intro = (
        "The repository sandbox is ready. Here is the bug report:\n\n"
        f"=== bug_report.md ===\n{report.strip()}\n=====================\n\n"
        "Investigate, reproduce, find the root cause, patch it, and verify. "
        "Start now."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_intro}]

    step = 1
    tool_calls_used = 0
    final_summary = ""
    stop_reason = None

    while tool_calls_used < MAX_TOOL_CALLS:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        stop_reason = response.stop_reason
        assistant_text = "".join(
            b.text for b in response.content if b.type == "text"
        ).strip()
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        messages.append({"role": "assistant", "content": response.content})

        if not tool_uses:
            final_summary = assistant_text
            trajectory.append({
                "step": step,
                "timestamp": now_iso(),
                "event": "final_message",
                "assistant_text": assistant_text,
                "stop_reason": stop_reason,
            })
            break

        tool_results = []
        for tu in tool_uses:
            tool_calls_used += 1
            try:
                fn = getattr(tools, tu.name)
                result_text = fn(**tu.input)
                is_error = False
            except Exception as exc:  # surface tool errors back to the model
                result_text = f"error: {exc}"
                is_error = True

            entry = {
                "step": step,
                "timestamp": now_iso(),
                "event": "tool_call",
                "decision": extract_decision(assistant_text),
                "tool": tu.name,
                "tool_input": dict(tu.input),
                "result_summary": summarize_result(
                    result_text, is_test_output=(tu.name == "run_tests")
                ),
                "is_error": is_error,
                "tool_calls_used": tool_calls_used,
                "verbose": {
                    "assistant_text": assistant_text,
                    "tool_result_raw": truncate(result_text),
                },
            }
            trajectory.append(entry)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": truncate(result_text),
                "is_error": is_error,
            })
            step += 1

            if tool_calls_used >= MAX_TOOL_CALLS:
                break

        messages.append({"role": "user", "content": tool_results})

        if tool_calls_used >= MAX_TOOL_CALLS:
            messages.append({
                "role": "user",
                "content": "You have reached the tool-call budget. Stop calling "
                           "tools and give your final report now: root cause "
                           "(file/line/why), the fix, and the test evidence.",
            })
            closing = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            final_summary = "".join(
                b.text for b in closing.content if b.type == "text"
            ).strip()
            trajectory.append({
                "step": step,
                "timestamp": now_iso(),
                "event": "final_message",
                "assistant_text": final_summary,
                "stop_reason": "tool_budget_exhausted",
            })
            break

    # ------------------------------------------------------------------ verdict
    final_run = tools.last_full_run or run_pytest(sandbox, None)
    after = final_run["outcomes"]
    now_passing = sorted(t for t in originally_failing if after.get(t) == "PASSED")
    still_failing = sorted(t for t in originally_failing if after.get(t) != "PASSED")
    regressions = sorted(t for t in originally_passing if after.get(t) != "PASSED")
    resolved = bool(originally_failing) and not still_failing and not regressions

    wall_seconds = round(time.perf_counter() - wall_start, 1)

    verdict = {
        "bug_id": bug_id,
        "resolved": resolved,
        "iterations_used": tool_calls_used,
        "max_iterations": MAX_TOOL_CALLS,
        "wall_clock_seconds": wall_seconds,
        "stop_reason": stop_reason,
        "originally_failing": sorted(originally_failing),
        "now_passing": now_passing,
        "still_failing": still_failing,
        "regressions": regressions,
        "final_test_summary": final_run["summary"],
        "agent_summary": final_summary,
        "sandbox": str(sandbox),
    }

    trajectory.append({
        "step": step + 1,
        "timestamp": now_iso(),
        "event": "verdict",
        **verdict,
    })

    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    traj_path = results_dir / f"{bug_id}_trajectory.json"
    traj_path.write_text(
        json.dumps({"verdict": verdict, "trajectory": trajectory}, indent=2),
        encoding="utf-8",
    )
    verdict["trajectory_file"] = str(traj_path)
    return verdict


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bug_dir", help="path to a bug directory, e.g. eval/bugs/bug_01")
    args = ap.parse_args()

    bug_dir = Path(args.bug_dir).resolve()
    if not (bug_dir / "repo").is_dir() or not (bug_dir / "bug_report.md").is_file():
        print(f"error: {bug_dir} is missing repo/ or bug_report.md", file=sys.stderr)
        return 2

    verdict = run_agent(bug_dir)

    print(f"bug id:                {verdict['bug_id']}")
    print(f"resolved:              {verdict['resolved']}")
    print(f"iterations used:       {verdict['iterations_used']} / {verdict['max_iterations']}")
    print(f"wall-clock time:       {verdict['wall_clock_seconds']}s")
    print(f"originally failing:    {verdict['originally_failing']}")
    print(f"now passing:           {verdict['now_passing']}")
    print(f"still failing:         {verdict['still_failing']}")
    print(f"regressions:           {verdict['regressions']}")
    print(f"final test summary:    {verdict['final_test_summary']}")
    print(f"trajectory:            {verdict['trajectory_file']}")
    print()
    print("agent summary of root cause & fix:")
    print(verdict["agent_summary"] or "(none)")

    return 0 if verdict["resolved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
