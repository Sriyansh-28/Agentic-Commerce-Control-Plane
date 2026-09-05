import hashlib
import hmac
import json

import pytest

from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import create_transaction
from backend.webhooks.handler import (
    is_duplicate_event,
    process_payment_webhook,
    verify_webhook_signature,
)


def create_authority():
    from datetime import datetime, timedelta, timezone

    return AuthorityEnvelope(
        authority_id="auth_webhook",
        agent_id="agent_001",
        allowed_action=ActionType.PURCHASE,
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=4000,
        currency="INR",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )


def create_executing_transaction():
    transaction = create_transaction(
        "txn_webhook_001",
        create_authority(),
        TransactionProposal(
            action=ActionType.PURCHASE,
            product_id="shoe_001",
            merchant_id="merchant_001",
            amount=3499,
            currency="INR",
            quantity=1,
        ),
    )

    transaction.state = TransactionState.EXECUTING.value

    return transaction


def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def test_valid_webhook_signature():
    payload = b'{"event":"payment.captured"}'
    secret = "webhook_secret"

    signature = sign_payload(payload, secret)

    assert verify_webhook_signature(
        payload,
        signature,
        secret,
    )


def test_invalid_webhook_signature_is_rejected():
    payload = b'{"event":"payment.captured"}'
    secret = "webhook_secret"

    assert not verify_webhook_signature(
        payload,
        "invalid_signature",
        secret,
    )


def test_duplicate_event_is_detected():
    event_id = "evt_test_001"

    assert is_duplicate_event(event_id) is False
    assert is_duplicate_event(event_id) is True


def test_different_events_are_not_duplicates():
    assert is_duplicate_event("evt_test_002") is False
    assert is_duplicate_event("evt_test_003") is False


def test_payment_captured_webhook_moves_transaction_to_captured():
    transaction = create_executing_transaction()

    secret = "webhook_secret"

    payload = json.dumps(
        {
            "event": "payment.captured",
        }
    ).encode()

    signature = sign_payload(payload, secret)

    result, was_duplicate = process_payment_webhook(
        event_id="evt_capture_001",
        payload=payload,
        transaction=transaction,
        signature=signature,
        webhook_secret=secret,
    )

    assert result.state == TransactionState.CAPTURED.value
    assert was_duplicate is False


def test_payment_failed_webhook_moves_transaction_to_failed():
    transaction = create_executing_transaction()

    secret = "webhook_secret"

    payload = json.dumps(
        {
            "event": "payment.failed",
        }
    ).encode()

    signature = sign_payload(payload, secret)

    result, was_duplicate = process_payment_webhook(
        event_id="evt_failure_001",
        payload=payload,
        transaction=transaction,
        signature=signature,
        webhook_secret=secret,
    )

    assert result.state == TransactionState.FAILED.value
    assert was_duplicate is False


def test_duplicate_webhook_does_not_capture_again():
    transaction = create_executing_transaction()

    secret = "webhook_secret"

    payload = json.dumps(
        {
            "event": "payment.captured",
        }
    ).encode()

    signature = sign_payload(payload, secret)

    first_result, first_was_duplicate = process_payment_webhook(
        event_id="evt_duplicate_001",
        payload=payload,
        transaction=transaction,
        signature=signature,
        webhook_secret=secret,
    )

    assert first_result.state == TransactionState.CAPTURED.value
    assert first_was_duplicate is False

    # A real duplicate should be ignored rather than changing
    # the transaction again.
    second_transaction = create_executing_transaction()

    second_result, second_was_duplicate = process_payment_webhook(
        event_id="evt_duplicate_001",
        payload=payload,
        transaction=second_transaction,
        signature=signature,
        webhook_secret=secret,
    )

    assert second_result.state == TransactionState.EXECUTING.value
    assert second_was_duplicate is True