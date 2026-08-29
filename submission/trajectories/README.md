# Representative trajectories

Three bugs, chosen to show the range of what the systems do. Each has two files:

| File | What it is |
|---|---|
| `<bug>_trajectory.json` | The **advanced agent's** full run — a `verdict` block (bottom line) plus a `trajectory` array. Each tool-call step carries `decision` (the model's one-line reason for that step), `tool`, `tool_input`, a short `result_summary`, and `verbose.tool_result_raw` (the untruncated tool output). |
| `<bug>_baseline_response.txt` | The **one-shot baseline's** raw model output for the same bug — reasoning followed by the corrected file(s). No steps; a single API call. |

Reading tip: the `verdict` block at the top of each JSON is the summary. The
"key steps" below point at the 2–3 steps that carry the interesting reasoning
so you don't have to read the whole array.

Both systems resolved all three bugs. Full 11-bug results are in
`eval/results/summary.md`; the evidence comparison is in
`eval/results/evidence_scorecard.md`.

---

## bug_01 — the clean minimal loop

`truncate(text, length)` returns `text[:length - 1]` instead of `text[:length]`
— an off-by-one that drops one character.

**Why it's here:** the simplest possible case, showing the full
investigate → reproduce → patch → verify loop with nothing else going on.

**Advanced trajectory — key steps:**

| Step | Tool | What it shows |
|---|---|---|
| 2 | `read_file stringutils.py` | the agent reads the source and spots `text[:length - 1]` |
| 3 | `run_tests` | **reproduces the reported failure before touching code** — the `decision` field states the root cause but says "verify by reproducing first" |
| 4 | `apply_patch stringutils.py` | one-line fix; the `apply_patch` result embeds an auto-checkpoint showing the full suite going to `7 passed` |

Final report at the last `final_message` step: root cause at
`stringutils.py:12`, the fix, and which two tests went red → green.

**Baseline (`bug_01_baseline_response.txt`):** the same one-line fix, correct,
in a single call — ~5 s, no reproduction step, no audit trail.

---

## bug_06 — cross-file reasoning

`tank_capacity_litres` (in `containers.py`) calls
`cylinder_volume(height_m, radius_m)`, but `mathlib.cylinder_volume` is defined
as `cylinder_volume(radius, height)`. The arguments are transposed. The bug is
only visible if you compare the **call site in one file** against the
**definition in another**.

**Why it's here:** the fix requires connecting two files. The tempting wrong
move — "fix" `mathlib.cylinder_volume`'s parameter order — would break a
separate test that calls it directly.

**Advanced trajectory — key steps:**

| Step | Tool | What it shows |
|---|---|---|
| 2 | `read_file containers.py` | reads the call: `cylinder_volume(height_m, radius_m)` |
| 3 | `read_file mathlib.py` | reads the definition: `def cylinder_volume(radius, height)` — **the two signatures side by side is the whole bug** |
| 5 | `apply_patch containers.py` | `decision` field: *"arguments in the wrong order — `cylinder_volume` expects `(radius, height)`, so height and radius are swapped."* Fix is at the **call site**, not the definition |

Final report explicitly notes `mathlib` was left untouched because it is
correct and is called directly elsewhere.

**Baseline (`bug_06_baseline_response.txt`):** correctly identifies the swapped
call and fixes `containers.py` only — again in one shot, again with no record
of having checked the `mathlib` signature.

---

## bug_11 — the "wrong hypothesis" trap (the experiment)

The bug report says a returning customer's total is too low and "looks like the
5% bonus was applied twice." The **real** cause is an off-by-one in
`get_price_tier` (`>` instead of `>=`) that mis-tiers a customer whose spend
lands exactly on a threshold, giving her the wrong coupon rate. The wrong-tier
discount happens to equal a doubled bonus to the cent. `calculate_total`
references the bonus in two places (correctly — they cancel), so a
"de-duplication" patch looks code-supported. A protected test
(`test_returning_bonus_stacks_with_loyalty_coupon`, customer *Owen* at spend
750) fails on that tempting fix.

This bug was **redesigned twice** to make the misdirection harder (see
`CHANGELOG.md` v2 / "Removed / abandoned experiments"). The finding:

> Neither system fell for it. Both independently rejected the report's framing
> and found the tier off-by-one — but both took markedly longer than usual.

| | wall-clock on bug_11 | typical |
|---|---|---|
| Baseline | 58.6 s | ~7 s |
| Advanced | 78.9 s | ~25 s |

**Advanced trajectory — key steps:**

| Step | Tool | What it shows |
|---|---|---|
| 2 | `search_code "calculate_total\|_returning_customer_bonus"` | the agent's **first move follows the report's framing** — it goes looking for the bonus/stacking code |
| 3 | `read_file pricing.py` | reads the actual code, sees `calculate_total` applies the bonus once and `get_price_tier` uses `>`; the hypothesis starts to shift |
| 5 | `run_tests test_pricing.py` | `decision`: *"I found the root cause. Let's verify by reproducing the failure first"* — the pivot is complete before any patch |
| 6 | `apply_patch pricing.py` | `>` → `>=` in `get_price_tier`; the auto-checkpoint shows all 6 tests green, including the Owen trap test |
| 7 | `final_message` | the report **explicitly names the red herring**: the double-bonus number is a coincidence, `calculate_total` is correct, and only customers exactly on a threshold (not Owen at 750) are affected |

Step 6's `decision` field is only a one-line digest — its
`verbose.assistant_text` (≈1.5 KB) has the agent's full worked derivation:
the reproduction, the `_tier_threshold(2) == 500` collision with Nadia's spend,
the `net` / coupon / total arithmetic back to `$160.00`, and why Owen at 750
(strictly `> 500`) was never affected. That step is the single richest piece of
reasoning in these three files.

**Baseline (`bug_11_baseline_response.txt`):** the one-shot model — which never
sees the tests, the protected trap, or Owen — opens with *"the reported 'double
bonus' framing turns out to be a red herring,"* computes
`_tier_threshold(2) = 100 * 5**1 = 500` itself, matches it to the customer's
spend, and fixes the `>` comparison. It reaches the same conclusion by
inspection alone.

**What this pair demonstrates:** on a small, fully-inspectable codebase a
capable model is not reliably fooled by a misleading report — so resolution
rate does not separate the two systems here. The difference is that the
advanced run leaves a checkable record (reproduced failure at step 5,
regression-checked patch at step 6); the baseline leaves a claim.
