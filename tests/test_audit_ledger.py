from backend.ledger.audit_ledger import (
    get_transaction_events,
    record_event,
)


def test_event_is_recorded():
    record_event(
        transaction_id="txn_ledger_001",
        event_type="TRANSACTION_CREATED",
        state="PROPOSED",
        details="Transaction created.",
    )

    events = get_transaction_events("txn_ledger_001")

    assert len(events) == 1
    assert events[0]["transaction_id"] == "txn_ledger_001"
    assert events[0]["event_type"] == "TRANSACTION_CREATED"
    assert events[0]["state"] == "PROPOSED"


def test_multiple_events_are_preserved():
    record_event(
        transaction_id="txn_ledger_002",
        event_type="VALIDATION",
        state="VALIDATING",
        details="Validation started.",
    )

    record_event(
        transaction_id="txn_ledger_002",
        event_type="AUTHORIZATION",
        state="AUTHORIZED",
        details="Transaction authorized.",
    )

    events = get_transaction_events("txn_ledger_002")

    assert len(events) == 2
    assert events[0]["state"] == "VALIDATING"
    assert events[1]["state"] == "AUTHORIZED"