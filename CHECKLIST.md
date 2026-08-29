# Frontier Engineering Challenge — Checklist

## Before kickoff

- [x] Agent tested
- [x] Repo skeleton in place
- [x] Trajectory logging confirmed — `eval/results/<id>_trajectory.json` per run
- [ ] Screen recorder tested
- [x] Evaluation tie-break order noted
- [x] IP boundary decided — none; all code written in-window
- [x] Rough industry direction picked — automated debugging of unfamiliar codebases

## At kickoff

- [x] Read PDF twice
- [x] Extracted acceptance tests / constraints / data
- [x] Picked scope — 13 self-contained Python bugs (11 synthetic + 2 real historical GitHub bugs); one-shot prompt vs. sandboxed agentic loop
- [x] Picked one advanced-improvement axis — verifiability of the fix (reproduction + internal re-verification + audit trail)

## During build

- [x] Baseline built, passing, and committed
- [x] Advanced solution iterating with changelog entries — v1–v4 in `CHANGELOG.md`
- [x] Trajectories saved per agent — `*_trajectory.json` (advanced), `*_baseline_response.txt` (baseline)
- [x] Consequential actions sandboxed — every read/write/test in `tempfile.mkdtemp()`; original `eval/bugs/` tree never touched; pre-existing test files read-only
- [x] Improvement numerically measured — `eval/run_all.py` (resolution: 13/13 both systems) + `eval/score_evidence.py` (evidence criteria)
- [x] Real-world bugs added — `bug_12` (humanize, issue #59/PR #113), `bug_13` (python-semver, issue #45/PR #46); verbatim pre-fix source, provenance in `ground_truth.md`

## Before submission

- [x] README complete — measured results and architectural capabilities kept separate; revised thesis stated
- [x] Background IP section filled — "none"
- [ ] REPRODUCE.md tested on clean clone — written with real commands and representative outputs; not yet re-run from a fresh clone
- [ ] Video scripted and recorded under 5 min
- [x] Representative trajectories selected — 4 curated in `submission/trajectories/`: `bug_01` (clean loop), `bug_06` (cross-file), `bug_11` (the trap), `bug_13` (verification-and-recovery event), with a judge-facing README
- [x] Credentials confirmed absent — API key only via `ANTHROPIC_API_KEY`; no keys, tokens, or `.env` in the repo
- [x] Qualification-gate self-check done — baseline + advanced both run end to end, improvement measured, honest limitation documented
- [ ] Submitted with buffer time

## Outstanding

1. Record the walkthrough video (< 5 min).
2. Re-run `REPRODUCE.md` from a fresh clone against the 13-bug set to confirm it is complete.
3. Final packaging and submission.
