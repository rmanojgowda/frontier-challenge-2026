#!/usr/bin/env python3
"""Score the baseline and the advanced agent against the evidence criteria.

Reads ONLY existing artifacts -- no API calls:

  * advanced:      eval/results/bug_XX_trajectory.json          (always present)
  * baseline:      eval/results/bug_XX_baseline_response.txt     (present once
                   response persistence was added to run_baseline.py)
  * ground truth:  eval/bugs/bug_XX/ground_truth.md             (for criterion 2b)

Writes eval/results/evidence_scorecard.md and .json.

READ THIS BEFORE QUOTING A NUMBER
--------------------------------
Criteria 1, 4, 5, 7 are **structural**: fixed by how each system is built. The
baseline is a single no-tools prompt by design, so it scores 0 on all four for
every bug -- that restates its architecture, it does not measure output quality.

Criterion 6 is **harness-level**: the runner executes pytest before and after
the patch for BOTH systems. Only the advanced agent also verifies internally.

Criterion 2 is a **weak** text check: does the explanation use code formatting
or cite a line number? It does NOT verify the explanation against the true root
cause, so both systems pass it trivially. Kept for continuity, not weight.

Criterion 2b is the **strict, meaningful** one: does the explanation explicitly
name the actual buggy function, taken from the `Function:` field of that bug's
ground_truth.md? This is the only criterion that checks the explanation against
an external source of truth. (bug_04's root cause is a module-level regex
constant with no `Function:` field, so 2b is n/a there.)

The aggregate section keeps every group separate. Do not sum them.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 on the standard streams so printing summaries containing →, —, π, …
# never crashes when stdout/stderr is a pipe on a non-UTF-8 locale (cp1252 on
# Windows). Same fix as run_baseline.py / run_agent.py.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "eval" / "results"
BUGS_DIR = REPO_ROOT / "eval" / "bugs"
BUGS = [f"bug_{i:02d}" for i in range(1, 12)]

# (number, key, label, group)
CRITERIA: list[tuple[str, str, str, str]] = [
    ("1",  "reproduces_failure",           "Reproduces the failure before patching",                     "structural"),
    ("2",  "identifies_root_cause",        "Uses code formatting / cites a line number (NOT verified vs. true root cause)", "data-dependent (weak)"),
    ("2b", "names_true_buggy_function",    "Explicitly names the actual buggy function (per ground_truth.md)",             "root-cause-verified"),
    ("3",  "shows_file_location",          "Names a specific file path",                                 "data-dependent (weak)"),
    ("4",  "demonstrates_fix_after_patch", "Re-runs tests after applying the patch",                     "structural"),
    ("5",  "checks_regression_suite",      "Re-runs the whole suite after the patch",                    "structural"),
    ("6",  "executable_verification",      "Harness runs pytest before/after externally",                "harness-level"),
    ("7",  "auditable_trajectory",         "Full step-by-step trajectory is recorded",                   "structural"),
]
NUM_OF = {k: n for n, k, _, _ in CRITERIA}
LABEL_OF = {k: lbl for _, k, lbl, _ in CRITERIA}
GROUP_OF = {k: g for _, k, _, g in CRITERIA}
GROUP_ORDER = ["structural", "data-dependent (weak)", "root-cause-verified", "harness-level"]

# --- text heuristics -------------------------------------------------------- #
_LINE_RE = re.compile(r"\bline\s+\d+\b|\b[\w/]+\.py:\d+\b", re.I)
_BACKTICK_ID_RE = re.compile(r"`([A-Za-z_]\w*(?:\([^`\n]*\))?)`")
_PYFILE_RE = re.compile(r"\b[\w./-]+\.py\b")
_GT_FUNC_RE = re.compile(r"^\s*[-*]\s*Function:\s*`([^`]+)`", re.M)


def _names_func_or_line(text: str) -> tuple[bool, dict]:
    line_refs = _LINE_RE.findall(text)
    ids = _BACKTICK_ID_RE.findall(text)
    return bool(line_refs or ids), {
        "line_refs": sorted(set(line_refs))[:5],
        "backtick_identifiers": sorted(set(ids))[:8],
    }


def _names_pyfile(text: str) -> tuple[bool, list[str]]:
    files = _PYFILE_RE.findall(text)
    return bool(files), sorted(set(files))[:5]


def _names_true_function(text: str, func: str | None) -> tuple[bool | None, dict]:
    """Strict: is ``func`` present as a code symbol (back-ticked or called)?

    A bare word-boundary match is deliberately NOT accepted -- 'allow' and
    'height' are ordinary English words and appear in prose about those bugs
    without referring to the function. We require ```func``` or ``func(``.
    """
    if not func:
        return None, {"note": "ground_truth.md has no 'Function:' field for this bug"}
    m = re.search(r"`" + re.escape(func) + r"`|\b" + re.escape(func) + r"\s*\(", text)
    return bool(m), {"target": func, "matched": m.group(0) if m else None}


def ground_truth_function(bug: str) -> str | None:
    path = BUGS_DIR / bug / "ground_truth.md"
    if not path.is_file():
        return None
    m = _GT_FUNC_RE.search(path.read_text(encoding="utf-8"))
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------- #
# advanced: read the trajectory JSON
# --------------------------------------------------------------------------- #
def score_advanced(bug: str, gt_func: str | None) -> dict:
    path = RESULTS / f"{bug}_trajectory.json"
    if not path.is_file():
        return {"available": False, "reason": f"{path.name} not found",
                "response_available": False, "scores": {k: None for _, k, _, _ in CRITERIA},
                "evidence": {}}

    data = json.loads(path.read_text(encoding="utf-8"))
    steps = [s for s in data.get("trajectory", []) if s.get("event") == "tool_call"]
    summary = (data.get("verdict") or {}).get("agent_summary", "") or ""

    patch_positions = [i for i, s in enumerate(steps) if s.get("tool") == "apply_patch"]
    first_patch = patch_positions[0] if patch_positions else None

    runs_before_patch = [
        i for i, s in enumerate(steps)
        if s.get("tool") == "run_tests" and (first_patch is None or i < first_patch)
    ]

    def _raw(step: dict) -> str:
        return json.dumps(step.get("verbose", {})) + " " + json.dumps(step.get("result_summary", ""))

    post_patch_checks: list[str] = []
    full_suite_after = False
    if first_patch is not None:
        for i, s in enumerate(steps):
            if s.get("tool") == "apply_patch" and i >= first_patch and "checkpoint" in _raw(s):
                post_patch_checks.append(f"step {s.get('step')}: apply_patch auto-checkpoint")
                if "checkpoint_outcomes" in _raw(s):
                    full_suite_after = True
            if s.get("tool") == "run_tests" and i > first_patch:
                post_patch_checks.append(f"step {s.get('step')}: run_tests")
                if not (s.get("tool_input") or {}).get("test_path"):
                    full_suite_after = True

    rc_hit, rc_ev = _names_func_or_line(summary)
    fl_hit, fl_ev = _names_pyfile(summary)
    fn_hit, fn_ev = _names_true_function(summary, gt_func)

    return {
        "available": True,
        "response_available": True,
        "scores": {
            "reproduces_failure": bool(runs_before_patch),
            "identifies_root_cause": rc_hit,
            "names_true_buggy_function": fn_hit,
            "shows_file_location": fl_hit,
            "demonstrates_fix_after_patch": bool(post_patch_checks),
            "checks_regression_suite": full_suite_after,
            "executable_verification": True,
            "auditable_trajectory": True,
        },
        "evidence": {
            "tool_sequence": [s.get("tool") for s in steps],
            "first_apply_patch_step": steps[first_patch].get("step") if first_patch is not None else None,
            "run_tests_before_patch_steps": [steps[i].get("step") for i in runs_before_patch],
            "post_patch_checks": post_patch_checks,
            "root_cause_signals": rc_ev,
            "file_signals": fl_ev,
            "true_function_check": fn_ev,
        },
    }


# --------------------------------------------------------------------------- #
# baseline: read the raw response text (criteria 1,4,5,7 are structural False)
# --------------------------------------------------------------------------- #
def score_baseline(bug: str, gt_func: str | None) -> dict:
    path = RESULTS / f"{bug}_baseline_response.txt"
    scores: dict[str, object] = {
        "reproduces_failure": False,
        "identifies_root_cause": None,
        "names_true_buggy_function": None,
        "shows_file_location": None,
        "demonstrates_fix_after_patch": False,
        "checks_regression_suite": False,
        "executable_verification": True,
        "auditable_trajectory": False,
    }

    if path.is_file():
        text = path.read_text(encoding="utf-8")
        rc_hit, rc_ev = _names_func_or_line(text)
        fl_hit, fl_ev = _names_pyfile(text)
        fn_hit, fn_ev = _names_true_function(text, gt_func)
        scores["identifies_root_cause"] = rc_hit
        scores["shows_file_location"] = fl_hit
        scores["names_true_buggy_function"] = fn_hit
        return {
            "available": True, "response_available": True, "scores": scores,
            "evidence": {
                "response_chars": len(text),
                "root_cause_signals": rc_ev,
                "file_signals": fl_ev,
                "true_function_check": fn_ev,
            },
        }

    return {
        "available": True, "response_available": False, "scores": scores,
        "evidence": {"note": (
            "no _baseline_response.txt for this bug -- baseline run predates "
            "response persistence in run_baseline.py; criteria 2, 2b, 3 not "
            "measurable from artifacts"
        )},
    }


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def per_criterion(rows: dict[str, dict], system: str, key: str) -> tuple[int, int]:
    num = den = 0
    for bug in BUGS:
        v = rows[bug][system]["scores"].get(key)
        if v is None:
            continue
        den += 1
        num += 1 if v else 0
    return num, den


def group_fraction(rows: dict[str, dict], system: str, group: str) -> tuple[int, int]:
    num = den = 0
    for _, k, _, g in CRITERIA:
        if g != group:
            continue
        n, d = per_criterion(rows, system, k)
        num += n
        den += d
    return num, den


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def cell(v: object) -> str:
    if v is None:
        return "n/a¹"
    return "yes" if v else "no"


def build_markdown(rows: dict[str, dict], gt_funcs: dict[str, str | None],
                   generated_at: str) -> str:
    out: list[str] = []
    out.append("# Evidence scorecard — baseline vs. advanced")
    out.append("")
    out.append(f"_Generated {generated_at} from existing artifacts. No API calls._")
    out.append("")
    out.append("## How to read this")
    out.append("")
    out.append("- **Structural criteria (1, 4, 5, 7)** are fixed by architecture. The "
               "baseline is a single no-tools prompt *by design*, so it scores 0 on all "
               "four for every bug. That restates its design; it is not a per-bug "
               "quality measurement.")
    out.append("- **Criterion 6** is harness-level: `run_baseline.py` / `run_agent.py` "
               "both run pytest before and after the patch, so external executable "
               "verification exists for **both**. Only the advanced agent *also* "
               "verifies internally.")
    out.append("- **Criterion 2 is a weak check** — it only asks whether the explanation "
               "uses back-tick code formatting or cites a line number. It is *not* "
               "checked against the true root cause, so both systems pass it trivially. "
               "Kept for continuity.")
    out.append("- **Criterion 2b is the strict, meaningful one** — it checks whether the "
               "explanation explicitly names the *actual* buggy function, taken from the "
               "`Function:` field of each bug's `ground_truth.md`. This is the only "
               "criterion that compares the explanation to an external source of truth.")
    out.append("- Aggregates are reported **per group**. Do not sum them.")
    out.append("")
    out.append("### Heuristics")
    out.append("")
    out.append("- **2 (weak)** — text matches `line <N>` / `file.py:<N>`, or contains a "
               "back-ticked identifier like `` `foo` `` / `` `foo(a, b)` ``.")
    out.append("- **2b (strict)** — the ground-truth function name appears as a code "
               "symbol: `` `name` `` or `name(`. A bare word match is rejected on "
               "purpose (`allow`, `height` are ordinary words that occur in prose about "
               "those bugs).")
    out.append("- **3** — text contains a `*.py` path.")
    out.append("")
    out.append("### Ground-truth function per bug")
    out.append("")
    out.append("| Bug | `Function:` in ground_truth.md |")
    out.append("| --- | --- |")
    for bug in BUGS:
        f = gt_funcs[bug]
        out.append(f"| {bug} | {'`' + f + '`' if f else '— (module-level; no Function field)'} |")
    out.append("")

    # ---- per-bug detail
    out.append("## Per-bug detail")
    out.append("")
    for bug in BUGS:
        out.append(f"### {bug}")
        out.append("")
        out.append("| # | Criterion | Group | Baseline | Advanced |")
        out.append("| - | --- | --- | --- | --- |")
        for num, key, label, group in CRITERIA:
            b = rows[bug]["baseline"]["scores"].get(key)
            a = rows[bug]["advanced"]["scores"].get(key)
            out.append(f"| {num} | {label} | {group} | {cell(b)} | {cell(a)} |")
        out.append("")

    # ---- aggregates
    out.append("## Aggregates (kept separate — do not sum)")
    out.append("")
    blurb = {
        "structural": "_Determined by architecture. Baseline was built to skip these steps._",
        "data-dependent (weak)": "_Weak text checks. Both systems pass trivially; not discriminating._",
        "root-cause-verified": "**The meaningful measurement.** _Explanation checked against "
                               "`ground_truth.md`. n/a for bug_04 (no `Function:` field)._",
        "harness-level": "_External to both systems; identical for both; not discriminating._",
    }
    for group in GROUP_ORDER:
        out.append(f"### {group}")
        out.append("")
        out.append(blurb[group])
        out.append("")
        out.append("| Criterion | Baseline | Advanced |")
        out.append("| --- | --- | --- |")
        for _, k, _, g in CRITERIA:
            if g != group:
                continue
            bn, bd = per_criterion(rows, "baseline", k)
            an, ad = per_criterion(rows, "advanced", k)
            out.append(f"| {NUM_OF[k]}. {LABEL_OF[k]} | {bn}/{bd} | {an}/{ad} |")
        bn, bd = group_fraction(rows, "baseline", group)
        an, ad = group_fraction(rows, "advanced", group)
        bpct = f"{100 * bn / bd:.0f}%" if bd else "—"
        apct = f"{100 * an / ad:.0f}%" if ad else "—"
        out.append(f"| **group total** | **{bn}/{bd} ({bpct})** | **{an}/{ad} ({apct})** |")
        out.append("")

    missing = [b for b in BUGS if not rows[b]["baseline"]["response_available"]]
    no_func = [b for b in BUGS if gt_funcs[b] is None]
    out.append("---")
    out.append("")
    if missing:
        out.append(f"¹ baseline criteria 2/2b/3 not measurable for: "
                   f"{', '.join(missing)} (no saved response file).")
    else:
        out.append("¹ every baseline response file is present.")
    if no_func:
        out.append("")
        out.append(f"¹ criterion 2b is n/a for {', '.join(no_func)} — its `ground_truth.md` "
                   "documents a module-level construct with no `Function:` field.")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    gt_funcs = {bug: ground_truth_function(bug) for bug in BUGS}

    rows: dict[str, dict] = {}
    for bug in BUGS:
        rows[bug] = {
            "baseline": score_baseline(bug, gt_funcs[bug]),
            "advanced": score_advanced(bug, gt_funcs[bug]),
        }

    aggregates: dict[str, dict] = {}
    for group in GROUP_ORDER:
        aggregates[group] = {}
        for system in ("baseline", "advanced"):
            num, den = group_fraction(rows, system, group)
            aggregates[group][system] = {
                "met": num,
                "measured": den,
                "pct": round(100 * num / den, 1) if den else None,
                "per_criterion": {
                    k: dict(zip(("met", "measured"), per_criterion(rows, system, k)))
                    for _, k, _, g in CRITERIA if g == group
                },
            }

    payload = {
        "generated_at": generated_at,
        "source": "eval/results/*_trajectory.json, *_baseline_response.txt, "
                  "eval/bugs/*/ground_truth.md (no API calls)",
        "ground_truth_functions": gt_funcs,
        "criteria": [
            {"num": n, "key": k, "label": lbl, "group": g}
            for n, k, lbl, g in CRITERIA
        ],
        "caveats": {
            "structural": "criteria 1,4,5,7 are fixed by architecture; baseline scores 0 "
                          "on all four for every bug by design -- not a quality signal",
            "criterion_2_is_weak": "criterion 2 only checks for code formatting / a line "
                                   "number, NOT against the true root cause; both systems "
                                   "pass it on every bug",
            "criterion_2b_is_the_real_one": "criterion 2b checks the explanation against "
                                            "the Function: field of ground_truth.md; it is "
                                            "the only criterion verified against truth. "
                                            "n/a for bug_04 (module-level regex, no "
                                            "Function field)",
            "harness_level": "criterion 6 is external verification done by the harness for "
                             "BOTH systems",
            "do_not_sum": "groups are reported separately on purpose",
        },
        "bugs": rows,
        "aggregates": aggregates,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "evidence_scorecard.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (RESULTS / "evidence_scorecard.md").write_text(build_markdown(rows, gt_funcs, generated_at), encoding="utf-8")

    # console digest
    print(f"scored {len(BUGS)} bugs from existing artifacts (no API calls)\n")
    print(f"{'group':<24} {'baseline':>16} {'advanced':>16}")
    print("-" * 58)
    for group in GROUP_ORDER:
        d = aggregates[group]
        b, a = d["baseline"], d["advanced"]
        bcell = f"{b['met']}/{b['measured']}" + (f" ({b['pct']:.0f}%)" if b["pct"] is not None else "")
        acell = f"{a['met']}/{a['measured']}" + (f" ({a['pct']:.0f}%)" if a["pct"] is not None else "")
        print(f"{group:<24} {bcell:>16} {acell:>16}")

    print("\ncriterion 2b (names the true buggy function) — per bug:")
    for bug in BUGS:
        b = rows[bug]["baseline"]["scores"]["names_true_buggy_function"]
        a = rows[bug]["advanced"]["scores"]["names_true_buggy_function"]
        f = gt_funcs[bug] or "(none)"
        print(f"  {bug}  target={f:<22} baseline={str(b):<5} advanced={str(a)}")

    print(f"\nwrote {RESULTS / 'evidence_scorecard.md'}")
    print(f"wrote {RESULTS / 'evidence_scorecard.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
