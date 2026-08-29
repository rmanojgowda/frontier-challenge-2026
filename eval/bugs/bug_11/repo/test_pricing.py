import pytest

from pricing import calculate_total, get_price_tier, _returning_customer_bonus

NADIA = {"name": "Nadia", "lifetime_spend": 500, "returning": True}
OWEN = {"name": "Owen", "lifetime_spend": 750, "returning": True}
PIA = {"name": "Pia", "lifetime_spend": 50, "returning": False}
QUINN = {"name": "Quinn", "lifetime_spend": 300, "returning": True}


def test_returning_customer_total_matches_quote():
    # Reported case: Nadia, a returning customer, applies LOYAL to a $200.00
    # subtotal. The quoted total is $160.00.
    items = [{"price": 50.0, "qty": 4}]
    assert calculate_total(items, NADIA, "LOYAL") == 160.00


def test_returning_bonus_stacks_with_loyalty_coupon():
    items = [{"price": 100.0, "qty": 3}]
    assert calculate_total(items, OWEN, "LOYAL") == 240.00


def test_non_returning_customer_gets_only_the_coupon():
    items = [{"price": 25.0, "qty": 4}]           # $100.00 subtotal
    assert calculate_total(items, PIA, "LOYAL") == 75.00


def test_bonus_applies_without_a_coupon():
    items = [{"price": 40.0, "qty": 5}]           # $200.00 subtotal
    assert calculate_total(items, QUINN, None) == 190.00


def test_returning_bonus_value():
    assert _returning_customer_bonus({"returning": True}) == 0.05
    assert _returning_customer_bonus({"returning": False}) == 0.0


def test_price_tier_lookups():
    assert get_price_tier({"lifetime_spend": 50}) == 0
    assert get_price_tier({"lifetime_spend": 300}) == 1
    assert get_price_tier({"lifetime_spend": 750}) == 2
    assert get_price_tier({"lifetime_spend": 3000}) == 3
