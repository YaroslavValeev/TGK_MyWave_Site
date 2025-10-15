
"""
Simple pricing calculator for Tour packages.
Base zone price + package multiplier + options sum - coupon
"""

def calculate_price(base_zone_price: int, package: str, options: dict = None, coupon_percent: float = 0.0) -> dict:
    """
    Returns a dict with calculated price and breakdown.
    - package: one of 'Base', 'Pro', 'Elite'
    - options: dict of option_name -> price
    - coupon_percent: 0.0 - 100.0
    """
    if package not in ('Base', 'Pro', 'Elite'):
        raise ValueError('Unknown package')

    multipliers = {
        'Base': 1.0,
        'Pro': 1.5,
        'Elite': 2.2
    }

    pkg_mult = multipliers[package]
    options = options or {}
    options_sum = sum([float(v) for v in options.values()])

    base = float(base_zone_price) * pkg_mult
    subtotal = base + options_sum
    coupon_discount = subtotal * (float(coupon_percent) / 100.0)
    total = int(round(subtotal - coupon_discount))

    return {
        'base_zone_price': base_zone_price,
        'package': package,
        'package_multiplier': pkg_mult,
        'options_sum': options_sum,
        'coupon_percent': coupon_percent,
        'total_price': total
    }
