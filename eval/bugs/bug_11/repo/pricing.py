"""Checkout pricing for the storefront.

``calculate_total`` combines the item subtotal, a coupon whose rate depends on
the customer's price tier, and a loyalty bonus for returning customers. Price
tiers are derived from a nightly snapshot of each customer's lifetime spend; the
``LOYAL`` coupon is our loyalty-tier coupon and is intentionally richer for
lower tiers, since higher-tier customers already receive standing discounts
elsewhere.
"""

_TIER_FLOOR = 100      # lifetime spend that lifts a customer out of tier 0
_TIER_GROWTH = 5       # each tier's threshold is this many times the previous
_MAX_TIER = 3

# Coupon discount as a fraction, indexed by price tier (0.._MAX_TIER).
_COUPON_RATES = {
    "LOYAL": [0.25, 0.20, 0.15, 0.10],
}

_RETURNING_BONUS = 0.05


def _tier_threshold(tier):
    """The lifetime-spend threshold for ``tier`` (1..``_MAX_TIER``)."""
    return _TIER_FLOOR * _TIER_GROWTH ** (tier - 1)


def get_price_tier(customer):
    """Return the customer's price tier (0..``_MAX_TIER``) from lifetime spend."""
    spend = customer["lifetime_spend"]
    tier = 0
    for candidate in range(1, _MAX_TIER + 1):
        if spend > _tier_threshold(candidate):
            tier = candidate
    return tier


def _coupon_rate(coupon, tier):
    """Discount fraction for ``coupon`` at price ``tier`` (0.0 if unknown)."""
    rates = _COUPON_RATES.get(coupon)
    if rates is None:
        return 0.0
    return rates[min(tier, len(rates) - 1)]


def _returning_customer_bonus(customer):
    """Return the fractional bonus for a returning customer (0.0 otherwise)."""
    if customer.get("returning"):
        return _RETURNING_BONUS
    return 0.0


def calculate_total(items, customer, coupon=None):
    """Return the final checkout total for ``items``, rounded to cents.

    Returning customers receive the loyalty bonus in addition to any coupon.
    """
    subtotal = sum(item["price"] * item["qty"] for item in items)
    bonus = _returning_customer_bonus(customer)
    tier = get_price_tier(customer)
    coupon_rate = _coupon_rate(coupon, tier)

    # The loyalty bonus comes off the cart first.
    net = subtotal * (1 - bonus)
    # The coupon rate is quoted against the full cart, so rebase it onto the
    # post-bonus amount before applying it.
    scaled_coupon = coupon_rate / (1 - bonus) if bonus else coupon_rate
    net = net * (1 - scaled_coupon)
    return round(net, 2)
