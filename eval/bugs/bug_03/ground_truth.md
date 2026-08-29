# Ground truth — bug_03 (Config loader, wrong fallback default)

**Scoring reference only. Not given to the agent.**

## Root cause

`appconfig.get_worker_count` uses the wrong fallback:

```python
return int(os.environ.get("APP_WORKERS", "0"))
```

When `APP_WORKERS` is unset it returns `0`. The documented and intended default
is `4`. Downstream, `partition` computes `size = len(items) // workers`, so a
zero worker count raises `ZeroDivisionError` on the first call. The bad default
is silent until something divides by it.

Note the other two getters (`get_batch_timeout` -> `"30"`, `get_region` ->
`"us-east-1"`) use correct defaults, which matches the reporter's observation
that only the worker count is affected.

## Correct fix

Use the intended default:

```python
return int(os.environ.get("APP_WORKERS", "4"))
```

Optional hardening (not required to pass the tests): clamp to at least 1, or
guard `partition` against `workers <= 0`. The minimal, correct fix is the
default value.

## Tests that should fail before the fix

- `test_appconfig.py::test_worker_count_default_is_four` — returns `0`, expected `4`
- `test_appconfig.py::test_partition_with_default_config` — raises `ZeroDivisionError`

Pass before and after: `test_worker_count_reads_env`, `test_batch_timeout_default`,
`test_region_default`.

## Location

- File: `eval/bugs/bug_03/repo/appconfig.py`
- Function: `get_worker_count`
- Line: `return int(os.environ.get("APP_WORKERS", "0"))`

## Difficulty

Easy. One-character-class change. The interesting part for the agent is tracing
the `ZeroDivisionError` in `partition` back to a *config default* two functions
away, rather than "fixing" `partition` with a guard and missing the real cause.
A guard in `partition` would make the crash go away but leave the pool size at 0
(all work in one chunk), so a good grader should prefer the default fix.
