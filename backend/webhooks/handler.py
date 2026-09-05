import hashlib
import hmac
import json

from backend.guardrails.schemas import Transaction
from backend.guardrails.transaction import TransactionState
from backend.ledger.audit_ledger import record_event


_processed_events: set[str] = set()


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify that a webhook was signed using the expected secret.
    """

    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature,
    )


def is_duplicate_event(event_id: str) -> bool:
    """
    Check whether a webhook event has already been processed.

    The first occurrence is marked as processed.
    Any later occurrence with the same event ID is treated
    as a duplicate.
    """

    if event_id in _processed_events:
        return True

    _processed_events.add(event_id)

    return False


def process_payment_webhook(
    event_id: str,
    payload: bytes,
    transaction: Transaction,
    signature: str,
    webhook_secret: str,
) -> tuple[Transaction, bool]:
    """
    Process a Razorpay payment webhook.

    The webhook must have a valid signature and must not have
    already been processed.

    Returns:
        (transaction, was_duplicate)

    where was_duplicate is True when the event was already
    processed and therefore ignored.
    """

    # 1. Verify webhook authenticity first.
    if not verify_webhook_signature(
        payload,
        signature,
        webhook_secret,
    ):
        raise ValueError("Invalid webhook signature.")

    # 2. Check webhook idempotency.
    if is_duplicate_event(event_id):
        record_event(
            transaction_id=transaction.transaction_id,
            event_type="DUPLICATE_WEBHOOK",
            state=transaction.state,
            details=(
                f"Webhook event '{event_id}' was already processed "
                "and was ignored."
            ),
        )

        # IMPORTANT:
        # Do not change the transaction state.
        #
        # For example:
        # CAPTURED -> CAPTURED
        #
        # Return True so the API layer can explicitly report
        # that this webhook was a duplicate.
        return transaction, True

    # 3. Parse the webhook payload.
    webhook_data = json.loads(
        payload.decode("utf-8")
    )

    event_type = webhook_data.get("event")

    # 4. Handle successful payment capture.
    if event_type == "payment.captured":
        if transaction.state != TransactionState.EXECUTING.value:
            raise ValueError(
                "Payment capture webhook requires an EXECUTING transaction."
            )

        transaction.state = TransactionState.CAPTURED.value

        record_event(
            transaction_id=transaction.transaction_id,
            event_type="PAYMENT_CAPTURED",
            state=TransactionState.CAPTURED.value,
            details=(
                f"Payment captured by Razorpay. "
                f"Event ID: {event_id}."
            ),
        )

    # 5. Handle failed payment.
    elif event_type == "payment.failed":
        if transaction.state != TransactionState.EXECUTING.value:
            raise ValueError(
                "Payment failure webhook requires an EXECUTING transaction."
            )

        transaction.state = TransactionState.FAILED.value

        record_event(
            transaction_id=transaction.transaction_id,
            event_type="PAYMENT_FAILED",
            state=TransactionState.FAILED.value,
            details=(
                f"Payment failed at Razorpay. "
                f"Event ID: {event_id}."
            ),
        )

    # 6. Record events we don't currently handle.
    else:
        record_event(
            transaction_id=transaction.transaction_id,
            event_type="UNHANDLED_WEBHOOK",
            state=transaction.state,
            details=(
                f"Webhook event '{event_type}' was received."
            ),
        )

    return transaction, False