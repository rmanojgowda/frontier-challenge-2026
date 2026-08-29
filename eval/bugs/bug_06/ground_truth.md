# Ground truth — bug_06 (Cross-file call, swapped argument order)

**Scoring reference only. Not given to the agent.**

## Root cause

`mathlib.cylinder_volume` is defined as `cylinder_volume(radius, height)`.

`containers.tank_capacity_litres(height_m, radius_m)` calls it with the
arguments in the order its *own* parameters appear:

```python
volume_m3 = cylinder_volume(height_m, radius_m)   # -> radius=height_m, height=radius_m
```

So `radius` and `height` are transposed. Because the volume formula is
`pi * r**2 * h`, the swap is not symmetric: it squares the wrong dimension.
`tank_capacity_litres(10, 2)` computes `pi * 10**2 * 2` instead of
`pi * 2**2 * 10` — a factor-of-5 error, exactly as reported.

`cylinder_volume` itself is correct (the direct-call test passes).
`fill_time_seconds` inherits the error through `tank_capacity_litres`.

## Correct fix

Pass the arguments in the order `cylinder_volume` expects (radius, then height):

```python
volume_m3 = cylinder_volume(radius_m, height_m)
```

Using keyword arguments is an equally good fix and prevents recurrence:

```python
volume_m3 = cylinder_volume(radius=radius_m, height=height_m)
```

Do **not** "fix" this by editing `mathlib.cylinder_volume`'s parameter order —
that function is correct and is also called directly elsewhere (and in the
tests).

## Tests that should fail before the fix

- `test_containers.py::test_tank_capacity_radius_2_height_10` — ~628,319 vs expected ~125,664
- `test_containers.py::test_fill_time` — off by the same factor of 5

Pass before and after: `test_cylinder_volume_direct`,
`test_tank_capacity_is_not_symmetric_in_its_args`.

## Location

- File: `eval/bugs/bug_06/repo/containers.py`
- Function: `tank_capacity_litres`
- Line: `volume_m3 = cylinder_volume(height_m, radius_m)`

## Difficulty

Medium. The failing test is in `containers` but the signature that matters is in
`mathlib` — the agent has to open both files and compare the parameter order at
the definition against the call site. Tempting wrong fix: swap the params in
`mathlib`, which breaks `test_cylinder_volume_direct`.
