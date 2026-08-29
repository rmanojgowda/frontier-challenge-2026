# Improvement Changelog

Implementation-level companion to the shorter summary in `README.md`. Same
v0–v4 story, more specifics per entry. Newest last.

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
- **Result:** 10/10 bugs resolved on the initial set (later 11/11, then 13/13
  after v4). ~6–8 s per bug. No investigation step, no test execution by the
  model, no retries, no record of the model's reasoning.
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
- **Result:** 11/11 resolved then (13/13 now) — **no change in resolution rate
  vs. the baseline.** 4–6 tool calls per bug, ~17–33 s per bug. What changed is
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
  identification tied 10/10** for both at the time (`bug_04` excluded — its root
  cause is a module-level regex constant with no single function; 12/12 for both
  after v4). Confirmed the differentiator is verifiability, not resolution rate
  and not diagnostic accuracy.
- **Agent(s) involved:** Claude Code.

## v4 — Two real historical GitHub bugs

- **Iteration:** v4 — `eval/bugs/bug_12`, `eval/bugs/bug_13`
- **Change:** added two bugs that are **unmodified open-source source at their
  historical pre-fix commits**, each with a real GitHub issue and a merged
  fixing PR, to sit alongside the 11 synthetic cases.

  - **`bug_12` — `humanize.intword`.** Real repo `jmoiron/humanize` (MIT).
    `intword` selects the magnitude word from the *unrounded* value but formats
    the mantissa with rounding, so a mantissa that rounds to `1000.0` keeps the
    smaller unit — `intword(999_999_999)` → `"1000.0 million"` instead of
    `"1.0 billion"`, at every tier. Reported as issues
    [#59](https://github.com/jmoiron/humanize/issues/59) / #64, fixed by PR
    [#113](https://github.com/jmoiron/humanize/pull/113) (merged 2020-03-05).
    Fixture: `repo/humanize/number.py` + `i18n.py` are verbatim at the pre-fix
    commit `b28d9ad895a1b2ef066c0b689b96bc50498554ba` (fix merge
    `86447e1b661dabdf888449e9e4a447ae59f495f3`); `number.py` sha1
    `3d388d4b9fb3393a7123497df32430d39328920c`. `__init__.py` is a minimal shim
    — the upstream one imports `pkg_resources` and locale catalogs unrelated to
    the bug. Verified: `3 failed / 4 passed` at the pre-fix commit; `7 passed`
    after the PR #113 `intword` hunk.

  - **`bug_13` — `python-semver` `nat_cmp`.** Real repo
    `python-semver/python-semver` (BSD-3-Clause). Pre-release precedence
    direction was inverted: in `nat_cmp`'s `convert()` helper, numeric
    identifiers were tagged `(2, …)` and text `(1, …)`, so a numeric identifier
    sorted *above* a text one — `compare("1.0.0-alpha.1", "1.0.0-alpha.beta")`
    → `1` instead of `-1`. Reported as issue
    [#45](https://github.com/python-semver/python-semver/issues/45), fixed by PR
    [#46](https://github.com/python-semver/python-semver/pull/46) (merged
    2017-01-16, released v2.7.4). Fixture: `repo/semver.py` is verbatim at the
    pre-fix commit `41a071595cdb400e625f366838b35d61d538ac7e` (v2.7.3; fix merge
    `4cac6fff9d7a530f358b65385658915e4f2a5caa`); sha1
    `3a9ee799fc72901e8f27f2581184adf720c2d778`. `repo/LICENSE.txt` is the
    upstream file. Verified: `3 failed / 3 passed` at the pre-fix commit;
    `6 passed` after the PR #46 `nat_cmp` rewrite.

  **`bug_13` was scoped twice.** The first attempt was built around
  `compare("1.0.0-beta.2", "1.0.0-beta.11")` and `compare("1.0.0-rc.1",
  "1.0.0")`. A verification gate before building found both **already pass** at
  the pre-fix commit `41a0715` — an earlier PR had fixed pure-lexicographic
  comparison, so by issue #45 / PR #46 only the numeric-vs-text *direction* and
  an (implicit, not actually broken) field-count tiebreak remained. The case was
  dropped and rebuilt around `compare("1.0.0-alpha.1", "1.0.0-alpha.beta")`,
  which genuinely returns `1` at the pre-fix commit. `ground_truth.md` documents
  this and is explicit about what is *not* broken at that revision.

  Each real bug ships a paraphrased user-voice `bug_report.md` (not copied from
  GitHub), evaluator tests for the reported vector plus protected
  already-passing vectors, and a `ground_truth.md` with repo / issue / PR / both
  commit hashes and the historical fix. `eval/run_all.py` and
  `eval/score_evidence.py` now cover `bug_01`–`bug_13`.
- **Evidence that motivated it:** the 11 synthetic cases are all tiny
  single-purpose files a strong model has effectively seen the shape of; we
  wanted at least two bugs from real projects and one substantially larger
  module.
- **Result:** **13/13 resolved by both systems, no regressions; strict
  root-cause identification 12/12 for both** (`bug_04` still n/a). No new
  capability gap. Advanced wall-clock is variable on the two real modules —
  `bug_12` 56 s / 4 iterations on one run, 92 s / 10 on another; `bug_13`
  123.6 s / 12 iterations — because both files exceed the `read_file` cap and
  can trigger the verification-and-recovery event (see the next entry).
  Baseline: `bug_12` ~28–36 s, `bug_13` 33.5 s.
- **Agent(s) involved:** Claude Sonnet 5 (both systems); Claude Code (source
  extraction, three-state verification, harness wiring).

## Observed verification-and-recovery events (individual runs)

**These are observed events from individual runs, not a measured improvement and
not a controlled comparison.** They are logged because they are instructive.

### The mechanism

Any file large enough to exceed the `read_file` tool's result cap (~6 KB) can be
returned **truncated** to the agent. A patch built from that partial view
silently drops or fabricates the unseen part of the file. This is then caught in
one of two ways:

- **by the automatic post-patch checkpoint**, if the resulting error breaks
  something the test suite exercises; or
- **by the agent's own re-reading and self-correction**, if the broken code is
  not exercised by any test.

Either way the loop converges on a correct, verified result. **A one-shot
architecture has no equivalent post-patch checkpoint in this workflow to detect
and recover from that kind of self-inflicted failure.** No claim is made about
what the baseline would do differently — in both runs below it received the full
file in its prompt (not through a length-capped tool) and resolved the bug in a
single call, so the truncation failure mode did not arise for it.

### Instance 1 — `bug_13`, checkpoint-detected

`bug_13`'s fixture is the verbatim `python-semver` module, 342 lines. In one
advanced run (trajectory `eval/results/bug_13_trajectory.json` /
`submission/trajectories/bug_13_trajectory.json`):

- **Step 2** `read_file semver.py` returned a **truncated** result (~5.4 KB of a
  ~10 KB file).
- **Step 4** `apply_patch` wrote a `semver.py` assembled from that partial view;
  it silently dropped everything after `match()`'s docstring. **Step-4
  checkpoint:** `1 error` (collection failed on the truncated module). The
  agent's next message: *"I truncated the file — I need to read the original
  full content beyond what was shown."*
- **Steps 5–12** — reconstruction (`read_file` / `search_code`) and a rewrite;
  checkpoint `6 passed`.
- **Verdict** — resolved, all three originally-failing tests pass, **zero
  regressions**, 12 of 15 iterations used.

### Instance 2 — `bug_12`, agent-detected (surfaced during clean-clone reproduction)

`bug_12`'s `number.py` is 213 lines — also over the cap. On a re-run during
clean-clone verification of `REPRODUCE.md`:

- **Step 4** `apply_patch` fixed `intword` correctly **but fabricated broken
  content in the unrelated `scientific()` function** (references to undefined
  names). Because `scientific()` is not exported by the fixture shim and not
  touched by any test, **the step-4 checkpoint passed clean (`7 passed`)** — it
  did not detect the fabrication.
- The agent noticed it anyway by re-reading (*"I clearly fabricated part of the
  `scientific` function since it was truncated in my initial read"*), rewrote
  the file cleanly at **step 10** (checkpoint `7 passed`), and finalized:
  resolved, **zero regressions**, 10 of 15 iterations.

### Note on how this was found

The truncation behaviour was **not designed in**. It was discovered to be
**file-size-triggered and nondeterministic — not `bug_13`-specific — during a
clean-clone reproduction test**, when a `bug_12` that had run cleanly in 4
iterations earlier hit the event on a fresh run. The reproduction process
surfacing a new, real behaviour is a small demonstration of it working as
intended. `bug_13` remains the primary curated example, now correctly framed as
one of at least two observed instances.

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
- **Why it didn't make the cut:** falsified by the experiment. 13/13 vs 13/13
  across the whole set, including the hardened trap and the two real historical
  bugs. The thesis in `README.md` is the revised version: the value is the
  verifiable record, not a better patch.
