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

None external. All 11 bugs are self-contained under `eval/bugs/bug_01` …
`eval/bugs/bug_11`. Each directory contains:

- `bug_report.md` — the only description given to either system
- `repo/` — the buggy source plus its pytest suite
- `ground_truth.md` — scoring reference (true root cause, tempting wrong fix,
  correct fix); **never shown to either system**

Nothing to download, no fixtures to generate. To confirm a bug is in its
expected failing state:

```bash
python -m pytest eval/bugs/bug_01/repo -q
# -> 1 or 2 failed, the rest passed
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
previously failing:     1  ['test_stringutils.py::test_truncate_longer_than_limit']
now passing:            1  ['test_stringutils.py::test_truncate_longer_than_limit']
still failing:          0  []
regressions:            0  []
bug fixed (all target tests pass, no regressions): True
api time:               3.9s
total wall-clock time:  6.3s
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

Full batch — both systems, all 11 bugs:

```bash
python eval/run_all.py
```

Writes `eval/results/summary.json` and `eval/results/summary.md`, and prints:

```
  bug      baseline         advanced
  ------------------------------------------
  bug_01   PASS 6.4s        PASS 17.3s (4it)
  bug_02   PASS 6.9s        PASS 32.5s (5it)
  ...
  bug_10   PASS 6.1s        PASS 19.3s (6it)
  bug_11   PASS 58.6s       PASS 78.9s (6it)
  ------------------------------------------
  Total    11/11 resolved   11/11 resolved
```

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
structural                      0/44 (0%)     44/44 (100%)
data-dependent (weak)        22/22 (100%)     22/22 (100%)
root-cause-verified          10/10 (100%)     10/10 (100%)
harness-level                11/11 (100%)     11/11 (100%)
```

## Cost & runtime

| Run | Wall-clock time | Cost | Machine / config |
|---|---|---|---|
| Baseline, one bug | ~6–8 s | ≪ $0.01 | one API call; laptop, CPU only |
| Advanced, one bug | ~17–33 s | ~$0.02–0.05 | 4–6 tool calls; laptop, CPU only |
| `bug_11`, either system (outlier) | 58–79 s | ~$0.05–0.15 | the "wrong hypothesis" trap; both systems reason ~3–8× longer |
| Full batch (`run_all.py`, 11 bugs × 2 systems) | ~9 min (measured: 396 s for bug_01–10, ~137 s for bug_11, total ≈530 s) | part of the project total below | one clean pass of both systems |
| `score_evidence.py` | < 1 s | $0 | no API calls |

**Measured total: $1.24 for the entire project** — all 11 bugs, both systems,
all debugging reruns, and bug_11's two redesign iterations (source: Claude
Console cost dashboard). The per-run figures above are rough estimates; the
$1.24 is the actual billed amount for everything.

Numbers vary run to run (API latency, and model nondeterminism in the
iteration count). Resolution outcomes have been stable across reruns.

## Known environment gotchas

- **Run from the repo root.** `run_all.py` invokes the other two scripts with
  `cwd` set to the root, but run by hand they resolve `eval/...` against your
  current directory.
- **Windows console encoding.** `run_baseline.py` and `run_agent.py` call
  `sys.stdout.reconfigure(encoding="utf-8")` so root-cause summaries containing
  `→` / `—` / `π` print cleanly when stdout is a pipe. On an older checkout
  without that line you get a `UnicodeEncodeError` on the final print — the fix
  itself and the trajectory JSON are still written; only the console echo
  fails.
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
