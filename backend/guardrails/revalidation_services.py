from backend.guardrails.policy import evaluate_transaction
from backend.guardrails.schemas import (
    AuthorityEnvelope,
    MerchantProduct,
    PolicyResult,
    Transaction,
)


def revalidate_transaction(
    transaction: Transaction,
    authority: AuthorityEnvelope,
    product: MerchantProduct,
) -> PolicyResult:
    """
    Revalidate an active transaction against the
    current merchant state.

    This check is deterministic. The AI agent does
    not participate in the authorization decision.
    """

    return evaluate_transaction(
        proposal=transaction.proposal,
        authority=authority,
        product=product,
    )