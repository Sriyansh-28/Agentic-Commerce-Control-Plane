from datetime import datetime, timezone

from backend.data.database import get_connection
from backend.guardrails.schemas import Transaction
from backend.guardrails.transaction_store import save_transaction


def save_transaction_to_db(transaction: Transaction) -> None:
    now = datetime.now(timezone.utc).isoformat()

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO transactions (
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
                razorpay_payment_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id)
            DO UPDATE SET
                state = excluded.state,
                razorpay_order_id = excluded.razorpay_order_id,
                razorpay_payment_id = excluded.razorpay_payment_id,
                updated_at = excluded.updated_at
            """,
            (
                transaction.transaction_id,
                transaction.authority_id,
                transaction.proposal.action.value,
                transaction.proposal.product_id,
                transaction.proposal.merchant_id,
                transaction.proposal.amount,
                transaction.proposal.currency,
                transaction.proposal.quantity,
                transaction.state,
                transaction.razorpay_order_id,
                transaction.razorpay_payment_id,
                now,
                now,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def persist_transaction(transaction: Transaction) -> None:
    """
    Persist a transaction to both the in-memory store and SQLite.
    """
    save_transaction(transaction)
    save_transaction_to_db(transaction)