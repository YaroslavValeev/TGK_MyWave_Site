import pytest
from app.utils.pricing import calculate_price


def test_base_package_no_options():
    res = calculate_price(10000, 'Base', options={}, coupon_percent=0.0)
    assert res['total_price'] == 10000


def test_pro_with_option_and_coupon():
    res = calculate_price(10000, 'Pro', options={'video': 2000}, coupon_percent=10.0)
    # base * 1.5 = 15000 + 2000 = 17000 - 10% = 15300
    assert res['total_price'] == 15300


def test_elite_rounding():
    res = calculate_price(12345, 'Elite', options={'merch': 555}, coupon_percent=5.0)
    assert isinstance(res['total_price'], int)


def test_unknown_package_raises():
    with pytest.raises(ValueError):
        calculate_price(10000, 'Unknown')
