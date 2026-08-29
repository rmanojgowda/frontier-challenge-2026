# Ground truth — bug_11 (Wrong-hypothesis trap: tier off-by-one disguised as a double-applied bonus)

**Scoring reference only. Not given to the agent.**

## Root cause

`pricing.get_price_tier` compares lifetime spend against each tier threshold
with a strict `>`:

```python
_TIER_FLOOR = 100      # tier 1 threshold
_TIER_GROWTH = 5       # each tier threshold is 5x the previous

def _tier_threshold(tier):
    return _TIER_FLOOR * _TIER_GROWTH ** (tier - 1)   # -> 100, 500, 2500

def get_price_tier(customer):
    spend = customer["lifetime_spend"]
    tier = 0
    for candidate in range(1, _MAX_TIER + 1):
        if spend > _tier_threshold(candidate):        # BUG: should be >=
            tier = candidate
    return tier
```

The tier-2 threshold is `100 * 5 == 500`. A customer whose `lifetime_spend` is
*exactly* a threshold is placed one tier too low. Nadia's lifetime spend is
exactly `500`, so she is scored tier 1 when she should be tier 2. The threshold
is computed, not listed, so this is only visible if you evaluate
`_tier_threshold(2)` and compare it to her spend.

The `LOYAL` coupon rate is indexed by tier — `[0.25, 0.20, 0.15, 0.10]` for
tiers 0..3 (loyalty coupons are intentionally richer at lower tiers). Tier 1
yields 20% where tier 2 should yield 15%. That extra 5 points of coupon is the
whole error: on Nadia's $200.00 subtotal it is $10.00.

`calculate_total` and `_returning_customer_bonus` are both correct.
`calculate_total` works in post-bonus space:

```python
net = subtotal * (1 - bonus)                       # bonus off the top
scaled_coupon = coupon_rate / (1 - bonus) if bonus else coupon_rate
net = net * (1 - scaled_coupon)
```

`bonus` appears in two places, but they cancel exactly:
`subtotal*(1-b) * (1 - c/(1-b)) == subtotal*(1 - b - c)`. The bonus is applied
once. This structure is a decoy — see below.

## Why it looks like a double-applied bonus

The returning-customer bonus is 5%. The coupon error is also 5 points. The two
explanations land on the same number:

| | effective discount | total on $200 |
|---|---|---|
| observed (buggy tier 1) | coupon 0.20 + bonus 0.05 = **0.25** | **$150.00** |
| "bonus applied twice" on the correct tier 2 | 0.15 + 0.05 + 0.05 = **0.25** | **$150.00** |

The bug report says the total is too low for a returning customer and "looks
like the bonus is taken twice". The visible `subtotal * (1 - bonus)` /
`coupon_rate / (1 - bonus)` pair in `calculate_total` seems to confirm a
double-count, and the arithmetic matches the observed total to the cent. It is
a coincidence — the bonus is applied exactly once and `calculate_total` is
correct.

## Tempting wrong fix (the trap)

Any change that removes the returning-customer bonus on a path where a coupon
is present. The cleanest-looking version, in `calculate_total`:

```python
bonus = _returning_customer_bonus(customer)
if coupon is not None:            # "the LOYAL coupon already prices in the returning discount"
    bonus = 0.0
```

- **Makes the reported test pass.** Nadia, still mis-scored as tier 1, gets
  coupon 0.20 with the bonus suppressed → `200 * (1 - 0.20) = $160.00`. Looks
  fixed.
- **Breaks `test_returning_bonus_stacks_with_loyalty_coupon`.** Owen's
  `lifetime_spend` is 750 — between the 500 and 2500 thresholds, unaffected by
  the off-by-one — so he is correctly tier 2, a returning customer using
  `LOYAL`. Correct total is `300 * (1 - 0.05 - 0.15) = $240.00`. With the bonus
  suppressed whenever a coupon is present he gets `300 * (1 - 0.15) = $255.00`,
  and the test fails.

That trap test exists precisely because the coupon and the returning bonus
*are* meant to stack. The reported symptom is not a stacking bug.

Other bonus-side edits are dead ends: removing the `/ (1 - bonus)` rebasing
gives Nadia `$152.00` (reported test still fails); dropping the up-front
`(1 - bonus)` gives `$157.89`. Deleting the bonus entirely also breaks
`test_bonus_applies_without_a_coupon`; zeroing `_returning_customer_bonus`
also breaks `test_returning_bonus_value`. Only suppressing the bonus when a
coupon is present makes the reported test pass while breaking *only* the trap.

## Correct fix

In `get_price_tier`, compare with `>=`:

```python
        if spend >= _tier_threshold(candidate):
            tier = candidate
```

Nadia becomes tier 2, her coupon rate becomes 15%, and her total is
`200 * (1 - 0.05 - 0.15) = $160.00`. Owen and everyone between thresholds are
unaffected. All six tests pass.

## Tests

Fails before the fix (exactly one):

- `test_pricing.py::test_returning_customer_total_matches_quote` — returns
  `150.0`, expected `160.0`

Passes before and after (must stay green):

- `test_pricing.py::test_returning_bonus_stacks_with_loyalty_coupon` — the trap
  detector; Owen's tier lookup is already correct, so his bonus must still
  stack with the coupon
- `test_pricing.py::test_non_returning_customer_gets_only_the_coupon`
- `test_pricing.py::test_bonus_applies_without_a_coupon`
- `test_pricing.py::test_returning_bonus_value`
- `test_pricing.py::test_price_tier_lookups` — only spends between thresholds,
  so it does not itself catch the boundary bug

## Location

- File: `eval/bugs/bug_11/repo/pricing.py`
- Function: `get_price_tier`
- Line: `if spend > _tier_threshold(candidate):`

## Difficulty

Hard. The bug report names the wrong mechanism, `calculate_total` genuinely
references `bonus` twice so a "de-duplication" patch looks code-supported, the
module docstring frames both `LOYAL` and the returning bonus as "loyalty" so
folding one into the other seems reasonable, and the tier thresholds are
computed rather than listed so the exact-boundary coincidence is not visible at
a glance. Nothing in the code contradicts the buggy `>`. To get it right an
agent has to disbelieve the report, work out that `_tier_threshold(2)` is
exactly 500, notice Nadia sits on it, and check `get_price_tier` at the
boundary. Running the full suite after the tempting fix is what exposes the
mistake — `test_returning_bonus_stacks_with_loyalty_coupon` turns red.
