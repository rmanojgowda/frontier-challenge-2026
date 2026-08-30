# Evidence-Driven Automated Debugging

Two automated debugging systems — a one-shot baseline and a sandboxed agentic
loop — run head-to-head over 13 bugs (11 hand-written synthetic cases plus two
real historical bugs lifted from open-source projects at their pre-fix commits).
The systems are compared on two things kept strictly separate throughout this
document: **what they measurably achieved** (resolution rate, root-cause
accuracy) and **what each architecture provides by design** (reproduction,
verification, an audit trail).

## Who this is for

Software developers and engineering teams who debug unfamiliar or complex
codebases — the case where you inherit a failing test or a bug report in code
you did not write, and most of the effort goes into understanding the system
well enough to trust a fix. Familiarity with Python, pytest, and tool-calling
LLM agents is assumed; no background in this project is needed.

## The bottleneck

Debugging unfamiliar code is a loop: **investigate → reproduce → fix →
verify**, repeated until the fix holds. Every pass is manual and serial. The
costly failure mode is not "no fix" — it is a **plausible but unverified fix**:
a change that matches the symptom and the reader's first hypothesis, passes the
one test everybody looked at, and quietly breaks something else or patches a
coincidence instead of the cause. Detecting that means redoing the
investigation — the exact work the fix was meant to save.

## Why it matters

- **Time.** The investigate–reproduce–verify loop is the slow part of most bug
  fixes and does not parallelize across a team.
- **Trust.** An unverified patch pushes risk downstream. Someone still has to
  reproduce the failure, confirm the diagnosis, and run the wider suite; if
  they skip it, the regression ships. A fix you cannot check is worth less than
  the effort it took to write.

## What existed before this competition

Nothing project-specific. Both systems, the evaluation harness, the 11 synthetic
bug cases, and the scoring code were all written during the competition window
(2026-08-28 to 2026-08-29). No prior internal tooling, no forked framework, no
pre-existing bug corpus. The two real bugs (`bug_12`, `bug_13`) are unmodified
source from open-source projects, checked out at their historical pre-fix
commits — see *The bug set* below.

## What I built

Both systems take the same input — a `bug_report.md` plus a small Python repo —
and produce a fix. The model is identical (`claude-sonnet-5`), so any
difference is architectural.

### Baseline — one-shot prompt

A single API call. The prompt carries the bug report and the full source of
every non-test file; the model returns corrected file(s), applied verbatim. No
tools, no investigation step, no test execution by the model, no retries. This
is the deliberate "basic approach" reference point.

### Advanced — sandboxed agentic loop

An agent loop (max 15 tool calls) with five tools over a throwaway sandbox copy
of the repo:

| Tool | Purpose |
|---|---|
| `list_files` | enumerate the repo |
| `read_file` | read a file with line numbers |
| `search_code` | regex across all `.py` files |
| `run_tests` | run pytest (whole suite or one node) in the sandbox |
| `apply_patch` | write a complete file, then auto-run the full suite as a checkpoint |

Harness guarantees: sandboxed execution (`tempfile.mkdtemp()`, the real
`eval/bugs/` tree is never touched); the test files present at setup are
read-only (`apply_patch` refuses to overwrite them — the agent may *add* a
test, not weaken an existing one); the full suite is re-run automatically after
every patch; every step (stated reasoning, tool, input, result digest,
timestamp) is logged to `eval/results/<bug_id>_trajectory.json`.

### The bug set

- **`bug_01`–`bug_11`** — hand-written synthetic bugs in tiny single-purpose
  modules: off-by-ones, a wrong caught-exception type, a greedy regex, a swapped
  cross-file call, a timezone bug, and `bug_11`, a purpose-built "wrong
  hypothesis" trap (twice-hardened).
- **`bug_12`** — a real bug in [`humanize`](https://github.com/jmoiron/humanize)
  (MIT). `intword()` rounds a mantissa up to `1000.0` but keeps the smaller unit
  word, so `intword(999_999_999)` returned `"1000.0 million"` instead of
  `"1.0 billion"`. Reported as issue
  [#59](https://github.com/jmoiron/humanize/issues/59) / #64, fixed by PR
  [#113](https://github.com/jmoiron/humanize/pull/113). Fixture source is the
  verbatim module at the pre-fix commit `b28d9ad`.
- **`bug_13`** — a real bug in
  [`python-semver`](https://github.com/python-semver/python-semver) (BSD-3).
  Pre-release precedence was inverted: a numeric identifier sorted *above* a
  text one, so `compare("1.0.0-alpha.1", "1.0.0-alpha.beta")` returned `1`
  instead of `-1`. Reported as issue
  [#45](https://github.com/python-semver/python-semver/issues/45), fixed by PR
  [#46](https://github.com/python-semver/python-semver/pull/46). Fixture source
  is the verbatim `semver.py` at the pre-fix commit `41a0715` (v2.7.3).

Each real bug ships a paraphrased user-voice `bug_report.md`, evaluator tests
covering the reported vector plus protected already-passing vectors, and a
`ground_truth.md` citing the repo, issue, PR, and both commit hashes. Full
provenance and the historical fix are in each `ground_truth.md` (never shown to
either system).

---

## Measured experimental results

These are the actual findings from running both systems over all 13 bugs. Each
number is produced by the harness executing pytest on a pristine copy before
and a patched copy after, or by `eval/score_evidence.py` reading stored
artifacts (no extra API calls).

### Our initial hypothesis was wrong

We expected the agentic loop to **resolve more bugs** than the one-shot model.
Across this 13-bug set, **it did not.** The two systems tied on resolution and
on root-cause accuracy.

### Resolution rate

| | Baseline | Advanced |
|---|---|---|
| Bugs resolved (all originally-failing tests pass, no regressions) | **13 / 13** | **13 / 13** |
| Typical wall-clock per bug (synthetic) | 6–8 s | 17–33 s |
| The two real bugs | 28–34 s | 56 s / 124 s |

`bug_11` is a "wrong hypothesis" trap: the bug report blames a double-applied
loyalty bonus; the real cause is an off-by-one in an unrelated price-tier
lookup; a protected test fails on the tempting wrong fix. It was **hardened
twice** after both systems solved earlier versions — computed tier thresholds
instead of a literal list, comments that do not contradict the buggy code, and
a `calculate_total` that genuinely references the bonus twice so a
"de-duplication" patch looks code-supported.

**Neither system fell for it.** Both identified the tier off-by-one and
explicitly rejected the double-bonus theory. The trap still had a real effect
on reasoning difficulty:

| | `bug_11` | typical |
|---|---|---|
| Baseline wall-clock | **58.6 s** | ~7 s |
| Advanced wall-clock | **78.9 s** | ~25 s |

Both systems took roughly an order of magnitude longer than usual before
arriving at the correct fix.

### Observed verification-and-recovery events

*These are observed events from individual runs, not a controlled
measured-improvement comparison. They are reported because they are instructive,
not as a scored result.*

**The mechanism.** Any file large enough to exceed the `read_file` tool's result
cap (~6 KB) can be returned **truncated** to the agent. A patch built from that
partial view silently drops or fabricates the unseen part of the file. This is
then caught in one of two ways:

- **by the automatic post-patch checkpoint** — if the resulting error breaks
  something the test suite exercises; or
- **by the agent's own re-reading and self-correction** — if the broken code is
  not exercised by any test.

Either way the loop converges on a correct, verified result. **A one-shot
architecture has no equivalent post-patch checkpoint in this workflow to detect
and recover from that kind of self-inflicted failure.** No claim is made about
what the baseline would do differently — in both runs below it received the full
file in its prompt (not through a length-capped tool) and resolved the bug in a
single call, so the truncation failure mode did not arise for it.

**Instance 1 — `bug_13`, checkpoint-detected (the primary curated example).**
`bug_13`'s fixture is the verbatim `python-semver` module, 342 lines. In one
advanced run: step 2 `read_file` returned ~5.4 KB of a ~10 KB file; step 4
`apply_patch` wrote a `semver.py` that dropped everything after `match()`'s
docstring; the step-4 checkpoint reported `1 error` (collection failed on the
broken module) and the agent's next message was *"I truncated the file — I need
to read the original full content beyond what was shown"*; steps 5–12
reconstructed and rewrote the module (checkpoint `6 passed`); verdict: resolved,
all three originally-failing tests pass, **zero regressions**, 12 of 15
iterations used. Trajectory: `submission/trajectories/bug_13_trajectory.json`.

**Instance 2 — `bug_12`, agent-detected (surfaced during clean-clone
reproduction).** `bug_12`'s `number.py` is 213 lines — also over the cap. On a
re-run during clean-clone verification of `REPRODUCE.md`, the agent's step-4
`apply_patch` fixed `intword` correctly **but fabricated broken content in the
unrelated `scientific()` function** (references to undefined names). Because
`scientific()` is not exported by the fixture shim and not touched by any test,
**the step-4 checkpoint passed clean (`7 passed`)** — it did not detect the
fabrication. The agent noticed it anyway by re-reading (*"I clearly fabricated
part of the `scientific` function since it was truncated in my initial read"*),
rewrote the file cleanly at step 10 (checkpoint `7 passed`), and finalized:
resolved, **zero regressions**, 10 of 15 iterations.

**This was not designed in.** The truncation behaviour was discovered to be
**file-size-triggered and nondeterministic — not `bug_13`-specific — during a
clean-clone reproduction test**, when the same `bug_12` that had run cleanly in
4 iterations earlier hit the event on a fresh run. That the reproduction process
surfaced a new, real behaviour is itself a small demonstration of it working as
intended.

### Root-cause identification (strict, against ground truth)

`eval/score_evidence.py` checks whether each explanation explicitly names the
**actual** buggy function, taken from the `Function:` field of that bug's
`ground_truth.md` — a bare word match is rejected, the name must appear as a
code symbol (`` `foo` ``, `foo(`, or opening a back-ticked expression such as
`` `foo.bar()` ``).

| | Baseline | Advanced |
|---|---|---|
| Names the true buggy function | **12 / 12** | **12 / 12** |

(`bug_04` is excluded from both: its root cause is a module-level regex
constant with no single function to name.)

### Summary of the measured result

On this bug set, with this model, the agentic architecture produced **no
advantage in bugs resolved and no advantage in diagnostic accuracy.** Both
systems solved everything — the 11 synthetic cases, the hardened trap, and the
two real historical bugs — and both correctly named the root cause every time
it was checkable.

The entire project cost **$3.44** in API spend (Claude Console cost dashboard,
month-to-date, checked 2026-08-30) — the 11 synthetic bugs, all debugging
reruns, `bug_11`'s two redesigns, the two real GitHub bugs including `bug_13`'s
dropped-and-rebuilt first attempt, all three clean-clone reproduction tests, and
the regex-fix verification reruns.

---

## Architectural capabilities

**What each system provides by design — not a measured performance difference.**

| Capability | Baseline | Advanced |
|---|---|---|
| Interactive investigation (read/search the repo before answering) | No | Yes |
| Pre-patch reproduction (runs the failing test before proposing a cause) | No | Yes |
| Iterative verification (can act on a test result and revise) | No | Yes |
| Regression checking within the agent's own loop | No | Yes |
| Auditable trajectory (step-by-step log of how the fix was reached) | No | Yes |
| Protected sandbox (isolated execution; original tests read-only) | No | Yes |

**Caption.** These are properties of each architecture, not measured
performance differences. The baseline was designed without these steps as a
fair "basic approach" comparison, per the hackathon's own guidance. The value
of the advanced system is not that it scores higher on the table above — it is
that the table above exists at all: each row is a step the system performs and
records, so its output is an artifact you can check rather than a claim you
have to trust.

---

## The real thesis (revised after experimentation)

> We built this expecting to show that agentic debugging solves more bugs than
> a one-shot model. It didn't, on this bug set. What the experiment showed
> instead: the value isn't a better patch, it's an independently verifiable
> record of how that patch was reached and confirmed.
>
> **From AI-generated answers to verifiable engineering actions.**

The baseline hands you a diff and a paragraph. The advanced system hands you
the failing test it reproduced, the diagnosis at a file and line, the patch,
the full suite green afterward, and a timestamped log of every step in between
— generated as a structural consequence of how it runs, not asserted after the
fact. As foundation models get better at being right in one shot, the gap that
remains is not correctness. It is the gap between a claim and a proof.

## Background IP disclosure

None. All code, the bug set, and the evaluation were written during the
competition window. No pre-existing intellectual property, proprietary methods,
or third-party assets beyond the open-source `anthropic` SDK and `pytest`.

## Agents & tools used

| Agent / tool | Role | Where used | Notes |
|---|---|---|---|
| Claude Sonnet 5 (`claude-sonnet-5`, Anthropic API) | The debugging model | Baseline **and** advanced — identical model, so the comparison isolates architecture | `max_tokens` 16000; advanced loop capped at 15 tool calls |
| Claude Code | Built the harness, the bug set, and the scoring scripts | Development only — not part of either measured system | — |
| pytest | Test execution: reproduction, checkpoints, before/after verdicts | Harness, both systems | `-p no:cacheprovider`, isolated temp dirs |

## Improvement Changelog

### v0 — Baseline

- **Iteration:** v0 — one-shot prompt
- **Change:** bug report + full non-test source in a single API call; returned
  files applied verbatim; harness runs pytest before/after.
- **Evidence that motivated it:** n/a — starting point.
- **Result:** 10/10 (later 11/11, then 13/13 — see v4) resolved; ~6–8 s per bug.
- **Agent(s) involved:** Claude Sonnet 5.

### v1 — Advanced agentic loop

- **Iteration:** v1 — 5-tool sandboxed agent
- **Change:** `list_files` / `read_file` / `search_code` / `run_tests` /
  `apply_patch` over a temp-dir sandbox; original test files protected;
  auto-checkpoint (full suite) after every patch; full trajectory JSON per bug.
- **Evidence that motivated it:** hypothesis that a one-shot model would ship
  plausible-but-unverified fixes that break protected tests.
- **Result:** **resolution rate unchanged (11/11 then, 13/13 now).** The change
  is entirely architectural: reproduction, iterative verification, and an audit
  trail now exist for every fix. ~17–33 s per bug, 4–6 tool calls.
- **Agent(s) involved:** Claude Sonnet 5 (agent), Claude Code (harness).

### v2 — `bug_11`, the "wrong hypothesis" trap

- **Iteration:** v2 — adversarial bug to force a baseline/advanced split
- **Change:** added a pricing-module bug whose report points at the wrong
  mechanism, with a protected test that fails on the tempting fix. Hardened
  twice after both systems solved the first two versions.
- **Evidence that motivated it:** v1 showed no resolution-rate gap on ordinary
  bugs; we wanted a case where one-shot diagnosis should fail.
- **Result:** **both systems still resolved it and both named the true root
  cause.** No capability gap — an ~8× slowdown for the baseline (58.6 s vs ~7 s
  typical) and ~3× for the advanced agent (78.9 s vs ~25 s typical). Recorded
  as a finding.
- **Agent(s) involved:** Claude Sonnet 5 (both systems), Claude Code (design +
  three-state verification).

### v3 — Evidence scorecard

- **Iteration:** v3 — `eval/score_evidence.py`
- **Change:** scored both systems on evidence criteria from stored artifacts
  (no API calls), grouped as structural / weak-text / strict-verified /
  harness-level and never blended into one number; added `run_baseline.py`
  response persistence so the baseline's reasoning is auditable too.
- **Evidence that motivated it:** needed to state the difference precisely
  rather than assert "the agent shows its work".
- **Result:** structural capabilities 0% vs 100% (by design); strict
  root-cause identification **tied 10/10** (at the time; 12/12 after `bug_12` /
  `bug_13`). Confirmed the differentiator is verifiability, not capability.
- **Agent(s) involved:** Claude Code.

### v4 — Two real historical GitHub bugs

- **Iteration:** v4 — `eval/bugs/bug_12` (humanize), `eval/bugs/bug_13`
  (python-semver)
- **Change:** added two bugs that are unmodified open-source source at their
  pre-fix commits, each with a real issue + merged PR. `bug_13`'s first scoping
  was dropped (its proposed vectors already passed at the pre-fix commit) and
  rebuilt around the vector that actually fails — full detail in `CHANGELOG.md`.
- **Evidence that motivated it:** the synthetic set is all tiny single-purpose
  files; we wanted at least two bugs the systems could not have seen and a
  larger real module.
- **Result:** **13/13 resolved by both systems; strict root-cause
  identification 12/12 for both.** No new capability gap. Both real modules
  (`bug_13`'s 342-line `semver.py`, `bug_12`'s 213-line `number.py`) are large
  enough to exceed the `read_file` cap, and each produced a
  verification-and-recovery event in some runs (see above).
- **Agent(s) involved:** Claude Sonnet 5 (both systems); Claude Code
  (extraction, verification, wiring).

## Main failure mode

Neither system failed to resolve any of the 13 bugs, so there is no resolution
failure to report. The honest limitation is **scope**: this finding holds for
*small, fully-inspectable codebases* debugged by a *highly capable model*. In
that regime a misleading bug report does not reliably fool the one-shot model —
it reads every line, checks the logic itself, and finds the real cause
regardless of what the report claims, so resolution rate cannot expose the
advanced system's value.

Whether the tie survives on **larger or less-inspectable codebases** — where
one shot cannot trace every path and seeing the specific test failure is what
disambiguates the fix — is **still largely untested and stated as a limitation,
not hidden.** The two real modules are a first small data point: both are large
enough that the agent's length-capped `read_file` returned a partial view, the
agent patched from it and damaged the file, and either the post-patch checkpoint
or the agent's own re-read caught it and drove several recovery iterations to a
correct result anyway (see *Observed verification-and-recovery events*). Two
runs are anecdotes, not a regime change; the advanced architecture is designed
for that regime and this evaluation still does not properly reach it.

## Hot take

**The agent proposes, the environment verifies.** Our first hypothesis —
agentic debugging resolves more bugs — was falsified by our own experiment.
That is a more useful result than confirming what we expected: it tells us
where agentic verification actually earns its cost. Not raw resolution — trust.
