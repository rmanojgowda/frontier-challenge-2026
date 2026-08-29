# Reproduction Guide

Someone starting from a clean environment can follow this top to bottom and
reproduce every number in `README.md`.

## Requirements

- **OS:** Linux, macOS, or Windows. Developed on Windows 11 (Git Bash);
  nothing platform-specific beyond the note under *Known environment gotchas*.
- **Runtime:** Python 3.10 or newer. `venv` and `pip` from the standard
  library. Developed against Python 3.10.11.
- **Key dependencies:** `anthropic` (the Anthropic SDK) and `pytest`. No pins
  required; developed against `pytest` 9.1.1 and a current `anthropic` SDK.
- **Hardware:** none special — CPU only, no GPU. Each bug repo is a few small
  files; sandboxes are temp-dir copies. A few hundred MB of disk is plenty.
- **Credentials:** an Anthropic API key in the `ANTHROPIC_API_KEY` environment
  variable. Both systems call `claude-sonnet-5`.

## Setup

```bash
git clone <repo-url>
cd frontier-challenge

python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:      .venv\Scripts\Activate.ps1
# Windows Git Bash:        source .venv/Scripts/activate

pip install anthropic pytest

# Linux / macOS / Git Bash:
export ANTHROPIC_API_KEY=sk-ant-...
# Windows PowerShell:
#   $env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Run every command below **from the repository root** — the scripts resolve
`eval/...` paths relative to the current directory.

## Data

None external. All 13 bugs are self-contained under `eval/bugs/bug_01` …
`eval/bugs/bug_13`. Each directory contains:

- `bug_report.md` — the only description given to either system
- `repo/` — the buggy source plus its pytest suite
- `ground_truth.md` — scoring reference (true root cause, tempting wrong fix,
  correct fix); **never shown to either system**

`bug_01`–`bug_11` are hand-written synthetic cases. `bug_12` and `bug_13` are
**real historical bugs** — unmodified source from open-source projects, checked
out at the commit just before the upstream fix:

| Bug | Project | License | Issue / PR | Pre-fix commit | Fix merge |
|---|---|---|---|---|---|
| `bug_12` | [`jmoiron/humanize`](https://github.com/jmoiron/humanize) — `intword` | MIT | issue [#59](https://github.com/jmoiron/humanize/issues/59) / #64 → PR [#113](https://github.com/jmoiron/humanize/pull/113) | `b28d9ad` | `86447e1` |
| `bug_13` | [`python-semver/python-semver`](https://github.com/python-semver/python-semver) — `nat_cmp` | BSD-3-Clause | issue [#45](https://github.com/python-semver/python-semver/issues/45) → PR [#46](https://github.com/python-semver/python-semver/pull/46) | `41a0715` (v2.7.3) | `4cac6ff` |

Full provenance, sha1s, and the historical fix are in each bug's
`ground_truth.md`.

Nothing to download, no fixtures to generate. To confirm a bug is in its
expected failing state:

```bash
python -m pytest eval/bugs/bug_01/repo -q     # -> 1 or 2 failed, the rest passed
python -m pytest eval/bugs/bug_12/repo -q     # -> 3 failed, 4 passed
python -m pytest eval/bugs/bug_13/repo -q     # -> 3 failed, 3 passed
```

## Running the baseline

```bash
python baseline/run_baseline.py eval/bugs/bug_01
```

Representative output:

```
bug id:                 bug_01
model:                  claude-sonnet-5
files changed by model: stringutils.py
previously failing:     2  ['test_stringutils.py::test_truncate_longer_than_limit', 'test_stringutils.py::test_truncate_keeps_all_requested_characters']
now passing:            2  ['test_stringutils.py::test_truncate_longer_than_limit', 'test_stringutils.py::test_truncate_keeps_all_requested_characters']
still failing:          0  []
regressions:            0  []
bug fixed (all target tests pass, no regressions): True
api time:               3.5s
total wall-clock time:  5.4s
raw model response:     eval/results/bug_01_baseline_response.txt
```

The model's full response (reasoning + returned files) is saved to
`eval/results/bug_01_baseline_response.txt`.

## Running the advanced solution

```bash
python advanced/run_agent.py eval/bugs/bug_01
```

Representative output (final report abridged):

```
bug id:                bug_01
resolved:              True
iterations used:       5 / 15
wall-clock time:       17.3s
originally failing:    ['test_stringutils.py::test_truncate_longer_than_limit', ...]
now passing:           ['test_stringutils.py::test_truncate_longer_than_limit', ...]
still failing:         []
regressions:           []
final test summary:    7 passed in 0.14s
trajectory:            eval/results/bug_01_trajectory.json

agent summary of root cause & fix:
Root cause: stringutils.py, line 12 ... text[:length - 1] should be text[:length] ...
```

The full step-by-step log (reasoning, tool, input, result digest, timestamp for
every step) is `eval/results/bug_01_trajectory.json`.

## Running the evaluation / benchmark

Full batch — both systems, all 13 bugs:

```bash
python eval/run_all.py
```

Writes `eval/results/summary.json` and `eval/results/summary.md`, and prints:

```
  bug      baseline         advanced
  --------------------------------------------
  bug_01   PASS 6.4s        PASS 17.3s (4it)
  bug_02   PASS 6.9s        PASS 32.5s (5it)
  bug_03   PASS 6.1s        PASS 18.5s (4it)
  bug_04   PASS 7.6s        PASS 32.6s (6it)
  bug_05   PASS 7.4s        PASS 23.4s (5it)
  bug_06   PASS 6.4s        PASS 26.6s (5it)
  bug_07   PASS 6.8s        PASS 20.8s (4it)
  bug_08   PASS 6.7s        PASS 30.2s (4it)
  bug_09   PASS 6.3s        PASS 30.1s (6it)
  bug_10   PASS 6.1s        PASS 19.3s (6it)
  bug_11   PASS 58.6s       PASS 78.9s (6it)
  bug_12   PASS 28.2s       PASS 56s (4it)
  bug_13   PASS 33.5s       PASS 123.6s (12it)
  --------------------------------------------
  Total    13/13 resolved   13/13 resolved
```

(`bug_13`'s 12 advanced iterations are the verification-and-recovery event
described in `README.md`; numbers vary run to run.)

Flags: `--bugs bug_03 bug_07` runs a subset (merged into the existing summary),
`--no-merge` overwrites instead of merging, `--timeout N` sets the per-run cap
(default 240 s; a run that exceeds it is recorded as `TIMEOUT`, not a crash).

Then the evidence scorecard — reads stored artifacts only, **no API calls**:

```bash
python eval/score_evidence.py
```

Writes `eval/results/evidence_scorecard.json` / `.md` and prints:

```
group                            baseline         advanced
----------------------------------------------------------
structural                      0/52 (0%)     52/52 (100%)
data-dependent (weak)        26/26 (100%)     26/26 (100%)
root-cause-verified          12/12 (100%)     12/12 (100%)
harness-level                13/13 (100%)     13/13 (100%)
```

(`root-cause-verified` is 12 not 13 because `bug_04`'s root cause is a
module-level constant with no `Function:` field.)

## Cost & runtime

| Run | Wall-clock time | Cost | Machine / config |
|---|---|---|---|
| Baseline, one synthetic bug | ~6–8 s | ≪ $0.01 | one API call; laptop, CPU only |
| Advanced, one synthetic bug | ~17–33 s | ~$0.02–0.05 | 4–6 tool calls; laptop, CPU only |
| `bug_11`, either system (trap outlier) | 58–79 s | ~$0.05–0.15 | the "wrong hypothesis" trap; both systems reason ~3–8× longer |
| `bug_13` advanced (recovery outlier) | ~120 s | ~$0.10–0.20 | 12 iterations — the read-truncation-and-recovery event; see README |
| Full batch (`run_all.py`, 13 bugs × 2 systems) | ~11 min (synthetic 11: ≈530 s; `bug_12` + `bug_13`: ≈240 s) | part of the project total below | one clean pass of both systems |
| `score_evidence.py` | < 1 s | $0 | no API calls |

**Measured total: $1.24** for the core project — the 11 synthetic bugs, both
systems, all debugging reruns, and `bug_11`'s two redesign iterations (source:
Claude Console cost dashboard). Adding `bug_12` and `bug_13` was two more
bug-runs on top (roughly $0.10; not separately metered). The per-run figures
above are rough estimates.

Numbers vary run to run (API latency, and model nondeterminism in the
iteration count). Resolution outcomes have been stable across reruns.

## Known environment gotchas

- **Run from the repo root.** `run_all.py` invokes the other two scripts with
  `cwd` set to the root, but run by hand they resolve `eval/...` against your
  current directory.
- **Windows console encoding.** All four scripts (`run_baseline.py`,
  `run_agent.py`, `eval/run_all.py`, `eval/score_evidence.py`) call
  `sys.stdout.reconfigure(encoding="utf-8")` so output containing `→` / `—` /
  `π` / `·` prints cleanly when stdout is a pipe. On an older checkout without
  that line you get a `UnicodeEncodeError` on a print — any file the script
  writes (trajectory JSON, scorecard, summary) is still produced; only the
  console echo and the exit code are affected.
- **`run_all.py` merges by default.** A partial run (`--bugs ...`) updates only
  those rows in `summary.json` and carries the rest forward. Use `--no-merge`
  for a clean slate.
- **API nondeterminism.** `iterations used` and wall-clock differ between runs;
  a single run is not a proof. Re-run if a result looks off.
- **Rate limits.** `run_all.py` runs sequentially on purpose and will not
  burst.
- **`apply_patch` rewrites whole files** with `\n` line endings. On a repo
  checked out with CRLF, a raw diff of the sandbox shows a full-file change for
  a one-line fix — cosmetic; the trajectory records the real edit.
- **`eval/results/` is the shared output dir.** Re-running a bug overwrites its
  `*_trajectory.json` / `*_baseline_response.txt`; re-running `run_all.py`
  rewrites `summary.*`; `score_evidence.py` rewrites `evidence_scorecard.*`.
