from datetime import datetime, timedelta, timezone

from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    MerchantProduct,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_service import validate_transaction


def create_authority():
    return AuthorityEnvelope(
        authority_id="auth_001",
        agent_id="agent_001",
        allowed_action=ActionType.PURCHASE,
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=4000,
        currency="INR",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )


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


def create_proposal():
    return TransactionProposal(
        action=ActionType.PURCHASE,
        product_id="shoe_001",
        merchant_id="merchant_001",
        amount=3499,
        currency="INR",
        quantity=1,
    )


def test_valid_transaction_becomes_authorized():
    state = validate_transaction(
        create_proposal(),
        create_authority(),
        create_product(),
    )

    assert state == TransactionState.AUTHORIZED


def test_price_change_blocks_transaction():
    product = create_product()
    product.price = 4799

    state = validate_transaction(
        create_proposal(),
        create_authority(),
        product,
    )

    assert state == TransactionState.BLOCKED


def test_over_budget_transaction_blocks():
    proposal = create_proposal()
    proposal.amount = 4500

    state = validate_transaction(
        proposal,
        create_authority(),
        create_product(),
    )

    assert state == TransactionState.BLOCKED