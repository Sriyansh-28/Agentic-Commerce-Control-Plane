import pytest

from backend.guardrails.authority_store import (
    create_authority,
    get_authority,
)


def test_authority_is_stored_and_retrieved():
    authority = create_authority(
        authority_id="auth_001",
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=4000,
    )

    stored_authority = get_authority("auth_001")

    assert stored_authority.authority_id == authority.authority_id
    assert stored_authority.max_amount == 4000
    assert stored_authority.merchant_id == "merchant_001"


def test_unknown_authority_is_rejected():
    with pytest.raises(KeyError):
        get_authority("does_not_exist")