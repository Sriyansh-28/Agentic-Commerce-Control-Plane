from datetime import datetime, timedelta, timezone

from backend.guardrails.policy import evaluate_transaction
from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    MerchantProduct,
    PolicyDecision,
    TransactionProposal,
)


def create_authority(max_amount: int = 4000):
    return AuthorityEnvelope(
        authority_id="auth_001",
        agent_id="buyer_agent_01",
        allowed_action=ActionType.PURCHASE,
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=max_amount,
        currency="INR",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )


def create_product(price: int = 3499, inventory: int = 8):
    return MerchantProduct(
        product_id="shoe_001",
        merchant_id="merchant_001",
        name="AeroRun X1",
        category="running_shoes",
        price=price,
        currency="INR",
        available_sizes=[8, 9, 10],
        inventory=inventory,
    )


def create_proposal(amount: int = 3499):
    return TransactionProposal(
        action=ActionType.PURCHASE,
        product_id="shoe_001",
        merchant_id="merchant_001",
        amount=amount,
        currency="INR",
        quantity=1,
    )


def test_valid_transaction_is_allowed():
    result = evaluate_transaction(
        create_proposal(),
        create_authority(),
        create_product(),
    )

    assert result.decision == PolicyDecision.ALLOW


def test_price_change_is_blocked():
    result = evaluate_transaction(
        create_proposal(amount=3499),
        create_authority(),
        create_product(price=4799),
    )

    assert result.decision == PolicyDecision.BLOCK
    assert any("price changed" in reason.lower() for reason in result.reasons)


def test_over_budget_transaction_is_blocked():
    result = evaluate_transaction(
        create_proposal(amount=5000),
        create_authority(),
        create_product(price=5000),
    )

    assert result.decision == PolicyDecision.BLOCK
    assert any("authorized maximum" in reason for reason in result.reasons)


def test_wrong_product_is_blocked():
    authority = create_authority()

    proposal = create_proposal()
    proposal.product_id = "shoe_999"

    product = create_product()

    result = evaluate_transaction(
        proposal,
        authority,
        product,
    )

    assert result.decision == PolicyDecision.BLOCK


def test_empty_inventory_is_blocked():
    result = evaluate_transaction(
        create_proposal(),
        create_authority(),
        create_product(inventory=0),
    )

    assert result.decision == PolicyDecision.BLOCK