from unittest.mock import Mock

import pytest

from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import create_transaction
from backend.payments.execution_service import PaymentExecutionService


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
        "txn_payment_001",
        create_authority(),
        create_proposal(),
    )

    transaction.state = TransactionState.AUTHORIZED.value

    return transaction


def test_authorized_transaction_calls_razorpay():
    razorpay_client = Mock()

    razorpay_client.create_order.return_value = {
        "id": "order_test_001",
        "status": "created",
        "amount": 349900,
        "currency": "INR",
    }

    service = PaymentExecutionService(
        razorpay_client=razorpay_client
    )

    transaction = create_authorized_transaction()

    result = service.execute(transaction)

    razorpay_client.create_order.assert_called_once_with(
        amount=3499,
        currency="INR",
        receipt="txn_payment_001",
        transaction_id="txn_payment_001",
    )

    assert result["transaction_id"] == "txn_payment_001"
    assert result["state"] == TransactionState.EXECUTING.value
    assert result["order_id"] == "order_test_001"
    assert result["amount"] == 349900
    assert result["currency"] == "INR"

    assert transaction.razorpay_order_id == "order_test_001"


def test_blocked_transaction_cannot_call_razorpay():
    razorpay_client = Mock()

    service = PaymentExecutionService(
        razorpay_client=razorpay_client
    )

    transaction = create_transaction(
        "txn_blocked_001",
        create_authority(),
        create_proposal(),
    )

    with pytest.raises(ValueError):
        service.execute(transaction)

    razorpay_client.create_order.assert_not_called()


def test_razorpay_failure_marks_transaction_failed():
    razorpay_client = Mock()

    razorpay_client.create_order.side_effect = Exception(
        "Razorpay unavailable"
    )

    service = PaymentExecutionService(
        razorpay_client=razorpay_client
    )

    transaction = create_authorized_transaction()

    with pytest.raises(
        Exception,
        match="Razorpay unavailable",
    ):
        service.execute(transaction)

    assert transaction.state == TransactionState.FAILED.value

    razorpay_client.create_order.assert_called_once_with(
        amount=3499,
        currency="INR",
        receipt="txn_payment_001",
        transaction_id="txn_payment_001",
    )