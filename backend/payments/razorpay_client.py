import os

import razorpay
from dotenv import load_dotenv


load_dotenv()


class RazorpayClient:
    """
    Thin wrapper around the Razorpay SDK.

    This module is responsible only for communicating
    with Razorpay. Authorization decisions remain outside
    this class.
    """

    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not key_id or not key_secret:
            raise RuntimeError(
                "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured."
            )

        self.client = razorpay.Client(
            auth=(key_id, key_secret)
        )

    def create_order(
        self,
        amount: int,
        currency: str,
        receipt: str,
        transaction_id: str,
    ) -> dict:
        """
        Create a Razorpay order.

        Razorpay expects the amount in the smallest
        currency unit, so INR rupees are converted to paise.

        The AgentGuard transaction ID is stored in the
        Razorpay order notes so webhook events can be
        mapped back to the correct transaction.
        """

        order_data = {
            "amount": amount * 100,
            "currency": currency,
            "receipt": receipt,
            "notes": {
                "transaction_id": transaction_id,
            },
        }

        return self.client.order.create(data=order_data)