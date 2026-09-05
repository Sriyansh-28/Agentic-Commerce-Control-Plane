import pytest

from backend.data.catalog_store import (
    add_product,
    get_product,
    update_product_price,
)
from backend.guardrails.schemas import MerchantProduct


def test_product_price_can_be_updated():
    product = MerchantProduct(
        product_id="price_test_001",
        merchant_id="merchant_001",
        name="Test Running Shoes",
        category="shoes",
        price=3499,
        currency="INR",
        available_sizes=[9],
        inventory=5,
    )

    add_product(product)

    updated_product = update_product_price(
        product_id="price_test_001",
        new_price=4799,
    )

    assert updated_product.price == 4799
    assert get_product("price_test_001").price == 4799


def test_product_price_cannot_be_zero_or_negative():
    product = MerchantProduct(
        product_id="price_test_002",
        merchant_id="merchant_001",
        name="Test Running Shoes",
        category="shoes",
        price=3499,
        currency="INR",
        available_sizes=[9],
        inventory=5,
    )

    add_product(product)

    with pytest.raises(ValueError):
        update_product_price(
            product_id="price_test_002",
            new_price=0,
        )