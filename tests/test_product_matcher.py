import pytest

from backend.agent.product_matcher import find_matching_product
from backend.data.catalog_store import add_product
from backend.guardrails.schemas import MerchantProduct, UserIntent


def create_product(
    product_id="shoe_001",
    name="Running Shoes",
    category="shoes",
    price=3499,
    sizes=None,
    inventory=5,
):
    return MerchantProduct(
        product_id=product_id,
        merchant_id="merchant_001",
        name=name,
        category=category,
        price=price,
        currency="INR",
        available_sizes=sizes or [8, 9, 10],
        inventory=inventory,
    )


def create_intent(
    category="shoes",
    size=9,
    max_amount=4000,
):
    return UserIntent(
        request="Buy size-9 running shoes under ₹4,000",
        category=category,
        size=size,
        max_amount=max_amount,
        currency="INR",
    )


def test_matching_product_is_found():
    product = create_product()
    add_product(product)

    intent = create_intent()

    result = find_matching_product(
        intent=intent,
        product_ids=["shoe_001"],
    )

    assert result.product_id == "shoe_001"
    assert result.price == 3499
    assert result.inventory == 5


def test_product_with_wrong_size_is_rejected():
    product = create_product(
        product_id="shoe_wrong_size",
        sizes=[8, 10],
    )
    add_product(product)

    intent = create_intent(size=9)

    with pytest.raises(ValueError):
        find_matching_product(
            intent=intent,
            product_ids=["shoe_wrong_size"],
        )


def test_product_over_budget_is_rejected():
    product = create_product(
        product_id="shoe_over_budget",
        price=4999,
    )
    add_product(product)

    intent = create_intent(max_amount=4000)

    with pytest.raises(ValueError):
        find_matching_product(
            intent=intent,
            product_ids=["shoe_over_budget"],
        )


def test_out_of_stock_product_is_rejected():
    product = create_product(
        product_id="shoe_out_of_stock",
        inventory=0,
    )
    add_product(product)

    intent = create_intent()

    with pytest.raises(ValueError):
        find_matching_product(
            intent=intent,
            product_ids=["shoe_out_of_stock"],
        )


def test_wrong_category_is_rejected():
    product = create_product(
        product_id="shirt_001",
        category="shirts",
    )
    add_product(product)

    intent = create_intent(category="shoes")

    with pytest.raises(ValueError):
        find_matching_product(
            intent=intent,
            product_ids=["shirt_001"],
        )


def test_lowest_priced_valid_product_is_selected():
    expensive = create_product(
        product_id="shoe_expensive",
        price=3800,
    )

    cheaper = create_product(
        product_id="shoe_cheaper",
        price=3499,
    )

    add_product(expensive)
    add_product(cheaper)

    intent = create_intent()

    result = find_matching_product(
        intent=intent,
        product_ids=[
            "shoe_expensive",
            "shoe_cheaper",
        ],
    )

    assert result.product_id == "shoe_cheaper"
    assert result.price == 3499