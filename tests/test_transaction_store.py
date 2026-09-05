import pytest

from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    TransactionProposal,
)
from backend.guardrails.transaction_manager import create_transaction
from backend.guardrails.transaction_store import (
    get_transaction,
    save_transaction,
)


def create_transaction_for_test():
    from datetime import datetime, timedelta, timezone

    authority = AuthorityEnvelope(
        authority_id="auth_store_001",
        agent_id="agent_001",
        allowed_action=ActionType.PURCHASE,
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=4000,
        currency="INR",
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

    return create_transaction(
        transaction_id="txn_store_001",
        authority=authority,
        proposal=proposal,
    )


def test_transaction_can_be_saved_and_retrieved():
    transaction = create_transaction_for_test()

    save_transaction(transaction)

    stored = get_transaction("txn_store_001")

    assert stored.transaction_id == "txn_store_001"
    assert stored.state == transaction.state


def test_unknown_transaction_is_rejected():
    with pytest.raises(KeyError):
        get_transaction("does_not_exist")