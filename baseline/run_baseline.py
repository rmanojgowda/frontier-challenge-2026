#!/usr/bin/env python3
"""The "one direct prompt" automated-debugging baseline.

Per the hackathon spec this is deliberately minimal:

  * read the bug report + the full non-test source of a bug repo
  * send ONE prompt to the Claude API asking for corrected file(s)
  * apply the returned file(s) to a throwaway copy of the repo
  * run pytest before and after, and report whether the previously-failing
    test(s) now pass and whether anything that used to pass regressed

No tool use. No retries. No investigation step.

Usage:
    python baseline/run_baseline.py eval/bugs/bug_01

Requires ANTHROPIC_API_KEY in the environment and the `anthropic` and `pytest`
packages installed.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import anthropic

# Force UTF-8 on the standard streams so printing the model's explanation (which
# can contain →, —, π, …) never crashes when stdout/stderr is a pipe on a
# non-UTF-8 locale (e.g. cp1252 on Windows).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000

TEST_FILE_RE = re.compile(r"(^test_.*\.py$)|(.*_test\.py$)|(^conftest\.py$)")
# a fenced block whose first line names the file, e.g.  # path: stringutils.py
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
FILENAME_RE = re.compile(r"^\s*#\s*(?:path|file|filename)\s*:\s*(.+?)\s*$", re.IGNORECASE)
# pytest -v line:  test_x.py::test_name PASSED [ 12%]
RESULT_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR)\b")


def is_test_file(name: str) -> bool:
    return bool(TEST_FILE_RE.match(name))


def read_source_files(repo: Path) -> dict[str, str]:
    """Return {relative_path: text} for every non-test .py file under repo/."""
    out: dict[str, str] = {}
    for path in sorted(repo.rglob("*.py")):
        rel = path.relative_to(repo).as_posix()
        if is_test_file(path.name):
            continue
        out[rel] = path.read_text(encoding="utf-8")
    return out


def build_prompt(bug_report: str, sources: dict[str, str]) -> str:
    parts = [
        "You are fixing a bug in a small Python project. Below is a bug report "
        "filed by a user, followed by the complete source of every non-test "
        "file in the project.",
        "",
        "=== BUG REPORT ===",
        bug_report.strip(),
        "",
        "=== SOURCE FILES ===",
    ]
    for rel, text in sources.items():
        parts += [f"--- {rel} ---", "```python", text.rstrip("\n"), "```", ""]
    parts += [
        "=== YOUR TASK ===",
        "Identify the single root-cause bug and fix it. Then, for EACH file you "
        "change, output the complete corrected file as a fenced code block whose "
        "FIRST line is a comment naming the file path relative to the project "
        "root, exactly like this:",
        "",
        "```python",
        "# path: stringutils.py",
        "<full corrected contents of stringutils.py>",
        "```",
        "",
        "Rules:",
        "- Output the ENTIRE file, not a diff or a snippet.",
        "- Only include files you actually changed.",
        "- Do not modify or create test files.",
        "- Keep the change as small as possible; fix the root cause, not symptoms.",
        "- A short explanation before the code blocks is fine, but the code "
        "blocks are what will be applied.",
    ]
    return "\n".join(parts)


def call_claude(prompt: str) -> tuple[str, float]:
    client = anthropic.Anthropic()
    start = time.perf_counter()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.perf_counter() - start
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, elapsed


def parse_patches(response_text: str) -> dict[str, str]:
    """Pull {relative_path: new_contents} out of the model response."""
    patches: dict[str, str] = {}
    for block in FENCE_RE.findall(response_text):
        lines = block.splitlines()
        if not lines:
            continue
        m = FILENAME_RE.match(lines[0])
        if not m:
            continue
        rel = m.group(1).strip().lstrip("./")
        body = "\n".join(lines[1:]).strip("\n") + "\n"
        patches[rel] = body
    return patches


def run_pytest(repo: Path) -> dict[str, str]:
    """Return {test_id: PASSED|FAILED|ERROR} for the repo copy."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(repo), "-v", "--tb=no",
         "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
    )
    results: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        m = RESULT_RE.match(line.strip())
        if m:
            results[m.group(1)] = m.group(2)
    return results


def apply_patches(src_repo: Path, patches: dict[str, str]) -> tuple[Path, list[str], list[str]]:
    """Copy src_repo to a temp dir and overwrite files named in patches."""
    dst = Path(tempfile.mkdtemp(prefix="baseline_patched_")) / "repo"
    shutil.copytree(src_repo, dst)
    applied, skipped = [], []
    for rel, body in patches.items():
        target = dst / rel
        if is_test_file(target.name):
            skipped.append(f"{rel} (test file — ignored)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(body, encoding="utf-8")
        applied.append(rel if existed else f"{rel} (new file)")
    return dst.parent, applied, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bug_dir", help="path to a bug directory, e.g. eval/bugs/bug_01")
    args = ap.parse_args()

    wall_start = time.perf_counter()

    bug_dir = Path(args.bug_dir).resolve()
    bug_id = bug_dir.name
    repo = bug_dir / "repo"
    report_path = bug_dir / "bug_report.md"

    if not repo.is_dir() or not report_path.is_file():
        print(f"error: {bug_dir} is missing repo/ or bug_report.md", file=sys.stderr)
        return 2

    bug_report = report_path.read_text(encoding="utf-8")
    sources = read_source_files(repo)
    if not sources:
        print(f"error: no non-test .py files found under {repo}", file=sys.stderr)
        return 2

    # 1. baseline pytest on a pristine copy
    pristine_root, _, _ = apply_patches(repo, {})
    before = run_pytest(pristine_root / "repo")
    previously_failing = {t for t, r in before.items() if r != "PASSED"}
    previously_passing = {t for t, r in before.items() if r == "PASSED"}

    # 2. one prompt to Claude
    prompt = build_prompt(bug_report, sources)
    response_text, api_seconds = call_claude(prompt)
    patches = parse_patches(response_text)

    # Persist the model's full raw response (reasoning + code blocks) so there
    # is an auditable record of what the baseline "thought", for later
    # comparison against ground_truth.md / the advanced agent's trajectory.
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    response_path = results_dir / f"{bug_id}_baseline_response.txt"
    response_path.write_text(response_text, encoding="utf-8")

    # 3. apply + re-run
    if patches:
        patched_root, applied, skipped = apply_patches(repo, patches)
        after = run_pytest(patched_root / "repo")
    else:
        applied, skipped = [], []
        after = before

    now_passing = sorted(t for t in previously_failing if after.get(t) == "PASSED")
    still_failing = sorted(t for t in previously_failing if after.get(t) != "PASSED")
    regressions = sorted(t for t in previously_passing if after.get(t) != "PASSED")

    wall_seconds = time.perf_counter() - wall_start
    fixed = bool(previously_failing) and not still_failing and not regressions

    print(f"bug id:                 {bug_id}")
    print(f"model:                  {MODEL}")
    print(f"files changed by model: {', '.join(applied) if applied else '(none)'}")
    if skipped:
        print(f"patches ignored:        {', '.join(skipped)}")
    print(f"previously failing:     {len(previously_failing)}  "
          f"{sorted(previously_failing)}")
    print(f"now passing:            {len(now_passing)}  {now_passing}")
    print(f"still failing:          {len(still_failing)}  {still_failing}")
    print(f"regressions:            {len(regressions)}  {regressions}")
    print(f"bug fixed (all target tests pass, no regressions): {fixed}")
    print(f"api time:               {api_seconds:.1f}s")
    print(f"total wall-clock time:  {wall_seconds:.1f}s")
    print(f"raw model response:     {response_path}")

    return 0 if fixed else 1


if __name__ == "__main__":
    raise SystemExit(main())
