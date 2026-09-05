import hashlib
import hmac
import os

from backend.guardrails.schemas import Transaction


def verify_payment_signature(
    transaction: Transaction,
    payment_id: str,
    signature: str,
) -> bool:
    """
    Verify that a Razorpay Checkout success response is authentic.

    The order ID used for verification comes from the server-created
    transaction record, not from the browser request.
    """

    secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not secret:
        raise RuntimeError(
            "RAZORPAY_KEY_SECRET is not configured."
        )

    if not transaction.razorpay_order_id:
        raise ValueError(
            "Transaction does not have a Razorpay order ID."
        )

    if not payment_id:
        raise ValueError(
            "Razorpay payment ID is required."
        )

    if not signature:
        raise ValueError(
            "Razorpay payment signature is required."
        )

    message = (
        f"{transaction.razorpay_order_id}|{payment_id}"
    ).encode("utf-8")

    generated_signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        generated_signature,
        signature,
    )