import pytest
from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import (
    create_transaction,
    execute_transaction,
    mark_transaction_captured,
    mark_transaction_failed,
)


def create_authority():
    from datetime import datetime, timedelta, timezone

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


def create_authorized_transaction():
    transaction = create_transaction(
        "txn_execution_test",
        create_authority(),
        create_proposal(),
    )

    transaction.state = TransactionState.AUTHORIZED.value

    return transaction


def test_authorized_transaction_can_execute():
    transaction = create_authorized_transaction()

    transaction = execute_transaction(transaction)

    assert transaction.state == TransactionState.EXECUTING.value


def test_executing_transaction_can_be_captured():
    transaction = create_authorized_transaction()

    transaction = execute_transaction(transaction)
    transaction = mark_transaction_captured(transaction)

    assert transaction.state == TransactionState.CAPTURED.value


def test_executing_transaction_can_fail():
    transaction = create_authorized_transaction()

    transaction = execute_transaction(transaction)
    transaction = mark_transaction_failed(transaction)

    assert transaction.state == TransactionState.FAILED.value


def test_non_authorized_transaction_cannot_execute():
    transaction = create_transaction(
        "txn_blocked",
        create_authority(),
        create_proposal(),
    )

    with pytest.raises(ValueError):
        execute_transaction(transaction)


def test_non_executing_transaction_cannot_be_captured():
    transaction = create_authorized_transaction()

    with pytest.raises(ValueError):
        mark_transaction_captured(transaction)