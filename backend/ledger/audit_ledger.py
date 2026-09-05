from datetime import datetime, timezone


_audit_events: list[dict] = []


def record_event(
    transaction_id: str,
    event_type: str,
    state: str,
    details: str,
) -> dict:
    """
    Record an immutable audit event for a transaction.
    """

    event = {
        "transaction_id": transaction_id,
        "event_type": event_type,
        "state": state,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _audit_events.append(event)

    return event


def get_transaction_events(transaction_id: str) -> list[dict]:
    """
    Return all audit events associated with a transaction.
    """

    return [
        event
        for event in _audit_events
        if event["transaction_id"] == transaction_id
    ]