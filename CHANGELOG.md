# Improvement Changelog

Implementation-level companion to the shorter summary in `README.md`. Same
v0–v3 story, more specifics per entry. Newest last.

## v0 — Baseline (one-shot prompt)

- **Iteration:** v0 — `baseline/run_baseline.py`
- **Change:** a single `messages.create` call to `claude-sonnet-5`
  (`max_tokens` 16000). The prompt is the bug report plus the full text of
  every non-test `.py` file in the repo, followed by an instruction to return
  each changed file as a fenced block whose first line is
  `# path: <relative/path>`. The harness parses those blocks (`FENCE_RE` +
  `FILENAME_RE`), copies the repo to a temp dir, writes the returned files
  (any test file in the response is silently skipped), and runs pytest before
  and after on separate pristine / patched copies. Verdict: every
  originally-failing test now passes and nothing that passed regressed.
- **Evidence that motivated it:** n/a — the honest "just ask the model"
  starting point and the fixed reference for every later comparison.
- **Result:** 10/10 bugs resolved on the initial set (later 11/11).
  ~6–8 s per bug. No investigation step, no test execution by the model, no
  retries, no record of the model's reasoning.
- **Agent(s) involved:** Claude Sonnet 5 (subject); Claude Code (harness).

## v1 — Advanced agentic loop

- **Iteration:** v1 — `advanced/run_agent.py`
- **Change:** replaced the single call with a tool-use loop (max 15 tool
  calls) over five tools:
  - `list_files` — recursive listing of the sandbox
  - `read_file` — file contents with line numbers
  - `search_code` — regex across every `*.py` in the sandbox, returns
    `file:line: matched-line`
  - `run_tests` — pytest in the sandbox, whole suite or a single
    `file.py::node`, with a 30 s timeout
  - `apply_patch` — write a complete file to a sandbox path

  Every tool operates on a `tempfile.mkdtemp()` copy of `repo/`; `safe_path()`
  rejects any path that resolves outside the sandbox root, so the real
  `eval/bugs/` tree is never a write target. The system prompt requires the
  agent to reproduce the reported failure before theorising, state the root
  cause with file and line, make the smallest fix, and confirm no regression.
  A per-bug `eval/results/<id>_trajectory.json` records the setup snapshot,
  every tool call, and the final verdict.
- **Evidence that motivated it:** the expectation that a one-shot model would
  emit plausible-but-unverified fixes — patching a symptom or a numeric
  coincidence — that a wider test run would catch.
- **Result:** 11/11 resolved — **no change in resolution rate vs. the
  baseline.** 4–6 tool calls per bug, ~17–33 s per bug. What changed is
  structural: reproduction, iterative verification, and an audit trail now
  exist for every fix.

  Two follow-up fixes within v1:

  - **Test-file write policy (two revisions).** The first cut let `apply_patch`
    write any file, including tests — which invites "fixing" a bug by editing
    the test that reports it. The second cut forbade all test-file writes —
    which also blocks the agent from adding a legitimate regression test. Final
    design: snapshot the set of test files that exist at setup
    (`collect_test_files`, matching `test_*.py` / `*_test.py` / `conftest.py`),
    and have `apply_patch` refuse writes only to *those* paths, while allowing
    brand-new test files. The refusal message states explicitly that this is a
    protection rule, not a sandbox-escape error, and suggests creating a new
    `test_regression.py` instead — so the agent doesn't burn turns retrying.
  - **Trajectory readability.** Raw tool output made the logs unreadable. Each
    step is now split into a short `result_summary` (for `run_tests`, the
    PASSED / FAILED / ERROR / assert lines are pulled to the front, then padded
    with leading context, capped at ~700 chars) and a
    `verbose.tool_result_raw` (full text, capped at 6000 chars). Added
    `extract_decision()` — the last substantive line of the model's reasoning
    before a call, collapsed to one line — as a `decision` field per step, and
    an auto-checkpoint block inside every `apply_patch` result
    (`checkpoint_summary` plus per-test `checkpoint_outcomes` from a full-suite
    re-run).
- **Agent(s) involved:** Claude Sonnet 5 (agent); Claude Code (harness and both
  follow-up fixes).

## v2 — `bug_11`, the "wrong hypothesis" trap

- **Iteration:** v2 — `eval/bugs/bug_11/`
- **Change:** a pricing module — `calculate_total`, `_returning_customer_bonus`,
  `get_price_tier`, `_coupon_rate`. The real bug: `get_price_tier` compares
  lifetime spend to each tier threshold with strict `>` instead of `>=`, so a
  customer whose spend is exactly on a boundary drops one tier and is charged
  the wrong tier-indexed coupon rate. `calculate_total` and
  `_returning_customer_bonus` are correct. The bug report describes only the
  symptom — "a returning customer's total is too low, looks like the bonus was
  applied twice" — and never mentions tiers; the wrong-tier discount happens to
  equal a doubled bonus to the cent. A protected test,
  `test_returning_bonus_stacks_with_loyalty_coupon`, uses a customer whose tier
  lookup was already correct and fails on the tempting fix (suppressing the
  bonus when a coupon is present). `ground_truth.md` documents the true cause,
  the tempting fix, and exactly which test it breaks and why. All three states
  verified by hand: buggy (one failing test), tempting fix (reported test
  passes, trap test fails, nothing else), real fix (all pass).
- **Evidence that motivated it:** v1 showed no resolution-rate gap on ordinary
  bugs. We wanted a case where confirmation bias from the report should make
  one-shot diagnosis fail while the agent's mandatory reproduce-and-verify loop
  saves it.
- **Result:** **the trap did not produce a differentiator.** Both systems
  resolved it; both explicitly named the tier off-by-one and rejected the
  double-bonus theory (the baseline, one-shot, wrote "which happens to look
  like 'double bonus' but is really just the wrong tier/coupon rate"). It did
  cost both — an ~8× slowdown for the baseline (58.6 s vs ~7 s typical) and ~3×
  for the advanced agent (78.9 s vs ~25 s typical) — so the misdirection
  measurably raised reasoning difficulty without changing the outcome. Kept as
  a documented finding.
- **Agent(s) involved:** Claude Sonnet 5 (both systems); Claude Code (bug
  design, two hardening passes, three-state verification).

## v3 — Evidence scorecard

- **Iteration:** v3 — `eval/score_evidence.py`, `eval/run_all.py`, baseline
  response persistence, a Windows encoding fix
- **Change:**
  - `run_baseline.py` now writes the model's full raw response to
    `eval/results/<id>_baseline_response.txt` after the call, so the baseline's
    reasoning is auditable rather than discarded once the fenced blocks are
    parsed out.
  - `run_all.py` batches both systems over `bug_01`–`bug_11` as subprocesses,
    parses each stdout for resolved / iterations / wall-clock, records a
    per-run crash or timeout as `error` / `timeout` without aborting the batch
    (default per-run timeout 240 s), and merges results into
    `summary.json` / `summary.md` — a partial `--bugs` run updates only those
    rows; `--no-merge` overwrites.
  - `score_evidence.py` scores both systems on evidence criteria read from
    stored artifacts only (no API calls), in groups that are **never blended
    into one number**:
    - *structural* — reproduces the failure before patching, re-runs tests
      after the patch, re-runs the whole suite, records a full trajectory:
      fixed by architecture (baseline 0, advanced 1 on every bug)
    - *data-dependent (weak)* — criteria 2 and 3: does the explanation use code
      formatting / cite a line, and does it name a `*.py` file
    - *root-cause-verified (strict)* — criterion 2b: does the explanation name
      the exact function from that bug's `ground_truth.md` `Function:` field,
      as a code symbol (`` `name` `` or `name(`); a bare word match is rejected
      because `allow` / `height` are ordinary words
    - *harness-level* — external pytest before/after, identical for both
  - `run_baseline.py` and `run_agent.py` now call
    `sys.stdout.reconfigure(encoding="utf-8")` /
    `sys.stderr.reconfigure(...)` right after imports, fixing a Windows-only
    `UnicodeEncodeError` when a root-cause summary containing `→` / `—` / `π`
    is printed to a pipe.
- **Evidence that motivated it:** needed to state the baseline-vs-advanced
  difference precisely instead of asserting "the agent shows its work" — and
  eight of the eleven baseline runs predated response persistence, so there was
  no saved reasoning to score until they were re-run.
- **Result:** structural capabilities 0/44 (0%) baseline vs 44/44 (100%)
  advanced — by design; weak text checks 22/22 for both; **strict root-cause
  identification tied 10/10** for both (`bug_04` excluded — its root cause is a
  module-level regex constant with no single function). Confirmed the
  differentiator is verifiability, not resolution rate and not diagnostic
  accuracy.
- **Agent(s) involved:** Claude Code.

## Removed / abandoned experiments

### `bug_11` designs 1 and 2

- **Tried:** design 1 listed the tier thresholds as
  `_TIER_MINIMUMS = [100, 500, 1000]` — so the boundary value sat literally in
  the source next to the customer's stated spend — and carried a docstring
  ("minimum spend to reach tier N") that contradicted the buggy `>`. Design 2
  fixed the docstring but kept the literal list and a `calculate_total` that
  referenced the bonus only once.
- **Why it didn't make the cut:** both were solved instantly by both systems,
  one-shot included. Replaced by the shipped design — thresholds computed as
  `_TIER_FLOOR * _TIER_GROWTH ** (tier - 1)`, directionally-neutral comments,
  and a `calculate_total` that genuinely references the bonus twice (once in an
  adjusted subtotal, once in a rebased coupon rate, algebraically cancelling)
  so a "de-duplication" patch looks code-supported. That version was also
  solved by both systems — see v2 — but it is the honest hardest form and is
  what ships.

### Single blended "evidence score"

- **Tried:** collapsing the seven criteria into one percentage per system.
- **Why it didn't make the cut:** it reads as "advanced ~95% vs baseline ~40%"
  when four criteria are true-by-construction for the advanced system and
  false-by-construction for the baseline. The scorecard reports each group
  separately and labels the structural ones as architectural, not measured.

### Expecting a resolution-rate gap

- **Tried:** the original project premise — that an agentic loop with execution
  and iteration would resolve bugs a one-shot model could not.
- **Why it didn't make the cut:** falsified by the experiment. 11/11 vs 11/11
  across the whole set, including the hardened trap. The thesis in `README.md`
  is the revised version: the value is the verifiable record, not a better
  patch.
