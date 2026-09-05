from datetime import datetime, timedelta, timezone

import pytest

from backend.guardrails.policy import evaluate_transaction, PolicyDecision
from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    MerchantProduct,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import execute_transaction


def create_authority(
    max_amount: int = 4000,
    expires_at: datetime | None = None,
):
    return AuthorityEnvelope(
        authority_id="auth_security_001",
        agent_id="agent_001",
        allowed_action=ActionType.PURCHASE,
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=max_amount,
        currency="INR",
        requires_inventory=True,
        requires_price_revalidation=True,
        expires_at=expires_at
        or datetime.now(timezone.utc) + timedelta(hours=1),
    )


def create_product(
    price: int = 3499,
    inventory: int = 5,
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


def create_proposal(
    amount: int = 3499,
):
    return TransactionProposal(
        action=ActionType.PURCHASE,
        product_id="shoe_001",
        merchant_id="merchant_001",
        amount=amount,
        currency="INR",
        quantity=1,
    )


def test_amount_above_authority_is_blocked():
    result = evaluate_transaction(
        proposal=create_proposal(amount=5000),
        authority=create_authority(max_amount=4000),
        product=create_product(),
    )

    assert result.decision == PolicyDecision.BLOCK
    assert any(
        "authority" in reason.lower()
        or "amount" in reason.lower()
        for reason in result.reasons
    )


def test_changed_price_is_blocked():
    result = evaluate_transaction(
        proposal=create_proposal(amount=3499),
        authority=create_authority(),
        product=create_product(price=4799),
    )

    assert result.decision == PolicyDecision.BLOCK
    assert any(
        "price changed" in reason.lower()
        for reason in result.reasons
    )


def test_wrong_merchant_is_blocked():
    product = create_product()
    product.merchant_id = "attacker_merchant"

    result = evaluate_transaction(
        proposal=create_proposal(),
        authority=create_authority(),
        product=product,
    )

    assert result.decision == PolicyDecision.BLOCK


def test_wrong_product_is_blocked():
    product = create_product()
    product.product_id = "different_product"

    result = evaluate_transaction(
        proposal=create_proposal(),
        authority=create_authority(),
        product=product,
    )

    assert result.decision == PolicyDecision.BLOCK


def test_empty_inventory_is_blocked():
    result = evaluate_transaction(
        proposal=create_proposal(),
        authority=create_authority(),
        product=create_product(inventory=0),
    )

    assert result.decision == PolicyDecision.BLOCK
    assert any(
        "inventory" in reason.lower()
        for reason in result.reasons
    )


def test_expired_authority_is_blocked():
    expired = datetime.now(timezone.utc) - timedelta(minutes=1)

    result = evaluate_transaction(
        proposal=create_proposal(),
        authority=create_authority(expires_at=expired),
        product=create_product(),
    )

    assert result.decision == PolicyDecision.BLOCK
    assert any(
        "expired" in reason.lower()
        for reason in result.reasons
    )


def test_non_authorized_transaction_cannot_execute():
    proposal = create_proposal()

    from backend.guardrails.schemas import Transaction

    transaction = Transaction(
        transaction_id="txn_security_001",
        authority_id="auth_security_001",
        proposal=proposal,
        state=TransactionState.BLOCKED.value,
    )

    with pytest.raises(ValueError, match="not AUTHORIZED"):
        execute_transaction(transaction)