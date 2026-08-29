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
- [x] Picked scope — 11 self-contained Python bugs; one-shot prompt vs. sandboxed agentic loop
- [x] Picked one advanced-improvement axis — verifiability of the fix (reproduction + internal re-verification + audit trail)

## During build

- [x] Baseline built, passing, and committed
- [x] Advanced solution iterating with changelog entries — v1–v3 in `CHANGELOG.md`
- [x] Trajectories saved per agent — `*_trajectory.json` (advanced), `*_baseline_response.txt` (baseline)
- [x] Consequential actions sandboxed — every read/write/test in `tempfile.mkdtemp()`; original `eval/bugs/` tree never touched; pre-existing test files read-only
- [x] Improvement numerically measured — `eval/run_all.py` (resolution) + `eval/score_evidence.py` (evidence criteria)

## Before submission

- [x] README complete — measured results and architectural capabilities kept separate; revised thesis stated
- [x] Background IP section filled — "none"
- [ ] REPRODUCE.md tested on clean clone — written with real commands and representative outputs; not yet re-run from a fresh clone
- [ ] Video scripted and recorded under 5 min
- [ ] Representative trajectories selected — candidates: `bug_11` (both systems, the trap), `bug_01` (clean minimal case)
- [x] Credentials confirmed absent — API key only via `ANTHROPIC_API_KEY`; no keys, tokens, or `.env` in the repo
- [x] Qualification-gate self-check done — baseline + advanced both run end to end, improvement measured, honest limitation documented
- [ ] Submitted with buffer time

## Outstanding

1. Record the walkthrough video (< 5 min).
2. Curate 1–2 representative trajectories into the submission.
3. Run `REPRODUCE.md` once from a fresh clone to confirm it is complete.
4. Final packaging and submission.
