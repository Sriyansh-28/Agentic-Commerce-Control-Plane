from .policy import evaluate_transaction
from .schemas import (
    AuthorityEnvelope,
    MerchantProduct,
    Transaction,
    TransactionProposal,
)
from .transaction import TransactionState


def create_transaction(
    transaction_id: str,
    authority: AuthorityEnvelope,
    proposal: TransactionProposal,
) -> Transaction:
    """
    Create a new transaction in the PROPOSED state.
    """

    return Transaction(
        transaction_id=transaction_id,
        authority_id=authority.authority_id,
        proposal=proposal,
        state=TransactionState.PROPOSED.value,
    )


def validate_transaction(
    transaction: Transaction,
    authority: AuthorityEnvelope,
    product: MerchantProduct,
) -> Transaction:
    """
    Revalidate the transaction against current authority
    and merchant state.
    """

    transaction.state = TransactionState.VALIDATING.value

    result = evaluate_transaction(
        proposal=transaction.proposal,
        authority=authority,
        product=product,
    )

    if result.decision.value == "ALLOW":
        transaction.state = TransactionState.AUTHORIZED.value
    else:
        transaction.state = TransactionState.BLOCKED.value

    return transaction


def execute_transaction(transaction: Transaction) -> Transaction:
    if transaction.state != TransactionState.AUTHORIZED:
        raise ValueError(
            "Payment cannot be executed because the transaction is not AUTHORIZED."
        )

    transaction.state = TransactionState.EXECUTING

    return transaction


def mark_transaction_captured(transaction: Transaction) -> Transaction:
    """
    Mark an executing transaction as successfully captured.
    """

    if transaction.state != TransactionState.EXECUTING.value:
        raise ValueError(
            "Only an EXECUTING transaction can be marked as CAPTURED."
        )

    transaction.state = TransactionState.CAPTURED.value

    return transaction


def mark_transaction_failed(transaction: Transaction) -> Transaction:
    """
    Mark an executing transaction as failed.
    """

    if transaction.state != TransactionState.EXECUTING.value:
        raise ValueError(
            "Only an EXECUTING transaction can be marked as FAILED."
        )

    transaction.state = TransactionState.FAILED.value

    return transaction