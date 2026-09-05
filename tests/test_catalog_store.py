import pytest

from backend.data.catalog_store import add_product, get_product
from backend.guardrails.schemas import MerchantProduct


def create_product():
    return MerchantProduct(
        product_id="shoe_001",
        merchant_id="merchant_001",
        name="Running Shoes",
        category="shoes",
        price=3499,
        currency="INR",
        available_sizes=[8, 9, 10],
        inventory=5,
    )


def test_product_is_stored_and_retrieved():
    product = create_product()

    add_product(product)

    stored_product = get_product("shoe_001")

    assert stored_product.product_id == "shoe_001"
    assert stored_product.price == 3499
    assert stored_product.inventory == 5


def test_unknown_product_is_rejected():
    with pytest.raises(KeyError):
        get_product("does_not_exist")