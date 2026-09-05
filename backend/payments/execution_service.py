from backend.guardrails.schemas import Transaction
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import execute_transaction
from backend.payments.razorpay_client import RazorpayClient
from dotenv import load_dotenv
from backend.data.persistence import persist_transaction

load_dotenv()


class PaymentExecutionService:
    """
    Controls the boundary between an authorized AgentGuard
    transaction and Razorpay.

    Razorpay is called only after the transaction has already
    been authorized by the policy layer.
    """

    def __init__(self, razorpay_client=None):
        self.razorpay_client = razorpay_client or RazorpayClient()

    def execute(self, transaction: Transaction) -> dict:
        """
        Execute an authorized transaction through Razorpay
        and return the Razorpay order details.
        """

        if transaction.state != TransactionState.AUTHORIZED.value:
            raise ValueError(
                "Payment execution requires an AUTHORIZED transaction."
            )

        try:
            transaction = execute_transaction(transaction)

            order = self.razorpay_client.create_order(
                amount=transaction.proposal.amount,
                currency=transaction.proposal.currency,
                receipt=transaction.transaction_id,
                transaction_id=transaction.transaction_id,
            )
            transaction.razorpay_order_id = order["id"]
            
            persist_transaction(transaction)

            return {
                "transaction_id": transaction.transaction_id,
                "state": transaction.state,
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "message": "Razorpay order created. Checkout can now be opened.",
            }

        except Exception:
            transaction.state = TransactionState.FAILED.value
            raise