from .policy import evaluate_transaction
from .schemas import (
    AuthorityEnvelope,
    MerchantProduct,
    PolicyDecision,
    TransactionProposal,
)
from .transaction import TransactionState


def validate_transaction(
    proposal: TransactionProposal,
    authority: AuthorityEnvelope,
    product: MerchantProduct,
) -> TransactionState:
    """
    Validate a proposed transaction against the user's authority
    and the merchant's current state.

    Returns the next transaction state.
    """

    result = evaluate_transaction(
        proposal=proposal,
        authority=authority,
        product=product,
    )

    if result.decision == PolicyDecision.ALLOW:
        return TransactionState.AUTHORIZED

    if result.decision == PolicyDecision.REAUTHORIZE:
        return TransactionState.REQUIRES_REAUTH

    return TransactionState.BLOCKED