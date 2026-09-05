from backend.data.database import get_connection
from backend.guardrails.schemas import (
    ActionType,
    Transaction,
    TransactionProposal,
)


_TRANSACTIONS: dict[str, Transaction] = {}


def save_transaction(transaction: Transaction) -> Transaction:
    """
    Store the current transaction state in the in-memory store.
    SQLite persistence is handled by the persistence layer.
    """
    _TRANSACTIONS[transaction.transaction_id] = transaction
    return transaction


def get_transaction(transaction_id: str) -> Transaction:
    """
    Retrieve a transaction from memory first.

    If it is not in memory, load it from SQLite so transactions
    survive backend restarts.
    """
    transaction = _TRANSACTIONS.get(transaction_id)

    if transaction is not None:
        return transaction

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                transaction_id,
                authority_id,
                action,
                product_id,
                merchant_id,
                amount,
                currency,
                quantity,
                state,
                razorpay_order_id,
                razorpay_payment_id
            FROM transactions
            WHERE transaction_id = ?
            """,
            (transaction_id,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise KeyError(
            f"Transaction '{transaction_id}' was not found."
        )

    proposal = TransactionProposal(
        action=ActionType(row["action"]),
        product_id=row["product_id"],
        merchant_id=row["merchant_id"],
        amount=row["amount"],
        currency=row["currency"],
        quantity=row["quantity"],
    )

    transaction = Transaction(
        transaction_id=row["transaction_id"],
        authority_id=row["authority_id"],
        proposal=proposal,
        state=row["state"],
        razorpay_order_id=row["razorpay_order_id"],
        razorpay_payment_id=row["razorpay_payment_id"],
    )

    _TRANSACTIONS[transaction_id] = transaction

    return transaction