from backend.guardrails.transaction import TransactionState


def test_transaction_starts_as_proposed():
    assert TransactionState.PROPOSED.value == "PROPOSED"


def test_transaction_can_be_captured():
    assert TransactionState.CAPTURED.value == "CAPTURED"


def test_blocked_state_exists():
    assert TransactionState.BLOCKED.value == "BLOCKED"


def test_duplicate_state_exists():
    assert TransactionState.DUPLICATE.value == "DUPLICATE"