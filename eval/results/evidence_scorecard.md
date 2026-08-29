# Evidence scorecard — baseline vs. advanced

_Generated 2026-08-29T12:59:38+00:00 from existing artifacts. No API calls._

## How to read this

- **Structural criteria (1, 4, 5, 7)** are fixed by architecture. The baseline is a single no-tools prompt *by design*, so it scores 0 on all four for every bug. That restates its design; it is not a per-bug quality measurement.
- **Criterion 6** is harness-level: `run_baseline.py` / `run_agent.py` both run pytest before and after the patch, so external executable verification exists for **both**. Only the advanced agent *also* verifies internally.
- **Criterion 2 is a weak check** — it only asks whether the explanation uses back-tick code formatting or cites a line number. It is *not* checked against the true root cause, so both systems pass it trivially. Kept for continuity.
- **Criterion 2b is the strict, meaningful one** — it checks whether the explanation explicitly names the *actual* buggy function, taken from the `Function:` field of each bug's `ground_truth.md`. This is the only criterion that compares the explanation to an external source of truth.
- Aggregates are reported **per group**. Do not sum them.

### Heuristics

- **2 (weak)** — text matches `line <N>` / `file.py:<N>`, or contains a back-ticked identifier like `` `foo` `` / `` `foo(a, b)` ``.
- **2b (strict)** — the ground-truth function name appears as a code symbol: `` `name` `` or `name(`. A bare word match is rejected on purpose (`allow`, `height` are ordinary words that occur in prose about those bugs).
- **3** — text contains a `*.py` path.

### Ground-truth function per bug

| Bug | `Function:` in ground_truth.md |
| --- | --- |
| bug_01 | `truncate` |
| bug_02 | `is_in_range` |
| bug_03 | `get_worker_count` |
| bug_04 | — (module-level; no Function field) |
| bug_05 | `update_name` |
| bug_06 | `tank_capacity_litres` |
| bug_07 | `event_day` |
| bug_08 | `rank_by_time` |
| bug_09 | `allow` |
| bug_10 | `height` |
| bug_11 | `get_price_tier` |
| bug_12 | `intword` |
| bug_13 | `nat_cmp` |

## Per-bug detail

### bug_01

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_02

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_03

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_04

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | n/a¹ | n/a¹ |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_05

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_06

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_07

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_08

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_09

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_10

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_11

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_12

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

### bug_13

| # | Criterion | Group | Baseline | Advanced |
| - | --- | --- | --- | --- |
| 1 | Reproduces the failure before patching | structural | no | yes |
| 2 | Uses code formatting / cites a line number (NOT verified vs. true root cause) | data-dependent (weak) | yes | yes |
| 2b | Explicitly names the actual buggy function (per ground_truth.md) | root-cause-verified | yes | yes |
| 3 | Names a specific file path | data-dependent (weak) | yes | yes |
| 4 | Re-runs tests after applying the patch | structural | no | yes |
| 5 | Re-runs the whole suite after the patch | structural | no | yes |
| 6 | Harness runs pytest before/after externally | harness-level | yes | yes |
| 7 | Full step-by-step trajectory is recorded | structural | no | yes |

## Aggregates (kept separate — do not sum)

### structural

_Determined by architecture. Baseline was built to skip these steps._

| Criterion | Baseline | Advanced |
| --- | --- | --- |
| 1. Reproduces the failure before patching | 0/13 | 13/13 |
| 4. Re-runs tests after applying the patch | 0/13 | 13/13 |
| 5. Re-runs the whole suite after the patch | 0/13 | 13/13 |
| 7. Full step-by-step trajectory is recorded | 0/13 | 13/13 |
| **group total** | **0/52 (0%)** | **52/52 (100%)** |

### data-dependent (weak)

_Weak text checks. Both systems pass trivially; not discriminating._

| Criterion | Baseline | Advanced |
| --- | --- | --- |
| 2. Uses code formatting / cites a line number (NOT verified vs. true root cause) | 13/13 | 13/13 |
| 3. Names a specific file path | 13/13 | 13/13 |
| **group total** | **26/26 (100%)** | **26/26 (100%)** |

### root-cause-verified

**The meaningful measurement.** _Explanation checked against `ground_truth.md`. n/a for bug_04 (no `Function:` field)._

| Criterion | Baseline | Advanced |
| --- | --- | --- |
| 2b. Explicitly names the actual buggy function (per ground_truth.md) | 12/12 | 12/12 |
| **group total** | **12/12 (100%)** | **12/12 (100%)** |

### harness-level

_External to both systems; identical for both; not discriminating._

| Criterion | Baseline | Advanced |
| --- | --- | --- |
| 6. Harness runs pytest before/after externally | 13/13 | 13/13 |
| **group total** | **13/13 (100%)** | **13/13 (100%)** |

---

¹ every baseline response file is present.

¹ criterion 2b is n/a for bug_04 — its `ground_truth.md` documents a module-level construct with no `Function:` field.
