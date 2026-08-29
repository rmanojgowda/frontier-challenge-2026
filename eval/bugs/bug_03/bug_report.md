# Jobs crash with ZeroDivisionError on a fresh deploy

**Component:** `appconfig`
**Severity:** high

## What happens

On a brand-new environment where we haven't set `APP_WORKERS` yet, the first
job that calls `partition()` dies immediately:

```
ZeroDivisionError: integer division or modulo by zero
  File "appconfig.py", line 27, in partition
    size = len(items) // workers
```

If I export `APP_WORKERS=4` by hand, everything works again.

## What I expected

The config is supposed to fall back to a default number of workers when the env
var isn't set, so a fresh deploy should just work. The README says the default
is 4.

## Repro

```python
# with APP_WORKERS unset
from appconfig import get_worker_count, partition
get_worker_count()        # -> 0   (expected 4)
partition(list(range(10)))  # -> ZeroDivisionError
```

## Notes

- `get_batch_timeout()` and `get_region()` both return correct defaults when
  their env vars are missing, so it's specific to the worker count.
