from datetime import datetime, timedelta, timezone

from backend.guardrails.revalidation_service import (
    revalidate_transaction,
)
from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    MerchantProduct,
    Transaction,
    TransactionProposal,
)


def create_test_data():
    authority = AuthorityEnvelope(
        authority_id="auth_revalidation_001",
        agent_id="agent_001",
        allowed_action=ActionType.PURCHASE,
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=4000,
        currency="INR",
        requires_inventory=True,
        requires_price_revalidation=True,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    proposal = TransactionProposal(
        action=ActionType.PURCHASE,
        product_id="shoe_001",
        merchant_id="merchant_001",
        amount=3499,
        currency="INR",
        quantity=1,
    )

    transaction = Transaction(
        transaction_id="txn_revalidation_001",
        authority_id=authority.authority_id,
        proposal=proposal,
        state="AUTHORIZED",
    )

    product = MerchantProduct(
        product_id="shoe_001",
        merchant_id="merchant_001",
        name="Running Shoes",
        category="shoes",
        price=3499,
        currency="INR",
        available_sizes=[8, 9, 10],
        inventory=5,
    )

    return transaction, authority, product


def test_revalidation_allows_unchanged_price():
    transaction, authority, product = create_test_data()

    result = revalidate_transaction(
        transaction=transaction,
        authority=authority,
        product=product,
    )

    assert result.decision.value == "ALLOW"


def test_revalidation_blocks_changed_price():
    transaction, authority, product = create_test_data()

    product.price = 4799

    result = revalidate_transaction(
        transaction=transaction,
        authority=authority,
        product=product,
    )

    assert result.decision.value == "BLOCK"

    assert any(
        "price changed" in reason.lower()
        for reason in result.reasons
    )