# Returning customer's checkout total comes out too low

**Component:** `pricing`
**Severity:** high

## What happens

Nadia is a returning customer. Her cart is a single line item — 4 units at
$50.00, a $200.00 subtotal — and she applies our `LOYAL` coupon.

The quote we gave her, and what the pricing sheet says she should pay, is
**$160.00**. `calculate_total` returns **$150.00**.

```python
>>> from pricing import calculate_total
>>> nadia = {"name": "Nadia", "lifetime_spend": 500, "returning": True}
>>> items = [{"price": 50.0, "qty": 4}]
>>> calculate_total(items, nadia, "LOYAL")
150.0        # expected 160.0
```

## What I expected

$160.00 — the `LOYAL` coupon and her returning-customer bonus, each applied
once.

## Notes

- $150.00 is *exactly* the number you get if the 5% returning-customer bonus is
  taken **twice** on top of the coupon. It really looks like the bonus and the
  coupon are stacking one time too many for her.
- `_returning_customer_bonus` on its own returns `0.05` for a returning
  customer, which is correct.
- Non-returning customers are billed correctly.
- I haven't audited every other returning customer, but the couple I spot-checked
  looked fine — this may be specific to Nadia's account.
