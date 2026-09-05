from datetime import datetime, timedelta, timezone

from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    MerchantProduct,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import (
    create_transaction,
    validate_transaction,
)


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


def create_proposal():
    return TransactionProposal(
        action=ActionType.PURCHASE,
        product_id="shoe_001",
        merchant_id="merchant_001",
        amount=3499,
        currency="INR",
        quantity=1,
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


def test_transaction_starts_as_proposed():
    transaction = create_transaction(
        "txn_001",
        create_authority(),
        create_proposal(),
    )

    assert transaction.state == TransactionState.PROPOSED.value


def test_valid_transaction_becomes_authorized():
    transaction = create_transaction(
        "txn_002",
        create_authority(),
        create_proposal(),
    )

    transaction = validate_transaction(
        transaction,
        create_authority(),
        create_product(),
    )

    assert transaction.state == TransactionState.AUTHORIZED.value


def test_price_change_blocks_transaction():
    transaction = create_transaction(
        "txn_003",
        create_authority(),
        create_proposal(),
    )

    product = create_product()
    product.price = 4799

    transaction = validate_transaction(
        transaction,
        create_authority(),
        product,
    )

    assert transaction.state == TransactionState.BLOCKED.value