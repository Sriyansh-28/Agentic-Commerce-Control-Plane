import pytest

from backend.agent.proposal_generator import create_purchase_proposal
from backend.guardrails.schemas import MerchantProduct, UserIntent


def create_product(
    price=3499,
    inventory=5,
):
    return MerchantProduct(
        product_id="shoe_001",
        merchant_id="merchant_001",
        name="Running Shoes",
        category="shoes",
        price=price,
        currency="INR",
        available_sizes=[8, 9, 10],
        inventory=inventory,
    )


def create_intent(max_amount=4000):
    return UserIntent(
        request="Buy size-9 running shoes under ₹4,000",
        category="shoes",
        size=9,
        max_amount=max_amount,
        currency="INR",
    )


def test_purchase_proposal_uses_authoritative_product_price():
    product = create_product(price=3499)
    intent = create_intent()

    proposal = create_purchase_proposal(
        intent=intent,
        product=product,
    )

    assert proposal.product_id == "shoe_001"
    assert proposal.merchant_id == "merchant_001"
    assert proposal.amount == 3499
    assert proposal.currency == "INR"
    assert proposal.quantity == 1


def test_purchase_proposal_supports_quantity():
    product = create_product(inventory=5)
    intent = create_intent()

    proposal = create_purchase_proposal(
        intent=intent,
        product=product,
        quantity=2,
    )

    assert proposal.quantity == 2
    assert proposal.amount == 3499


def test_quantity_cannot_exceed_inventory():
    product = create_product(inventory=1)
    intent = create_intent()

    with pytest.raises(ValueError):
        create_purchase_proposal(
            intent=intent,
            product=product,
            quantity=2,
        )


def test_price_above_budget_is_rejected():
    product = create_product(price=4500)
    intent = create_intent(max_amount=4000)

    with pytest.raises(ValueError):
        create_purchase_proposal(
            intent=intent,
            product=product,
        )


def test_zero_quantity_is_rejected():
    product = create_product()
    intent = create_intent()

    with pytest.raises(ValueError):
        create_purchase_proposal(
            intent=intent,
            product=product,
            quantity=0,
        )