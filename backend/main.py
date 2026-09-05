import json
import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.agent.purchase_service import process_purchase_request
from backend.data.catalog_store import (
    get_product,
    update_product_price,
)
from backend.data.seed import seed_demo_data
from backend.guardrails.authority_store import get_authority
from backend.guardrails.policy import evaluate_transaction
from backend.guardrails.revalidation_service import (
    revalidate_transaction,
)
from backend.guardrails.schemas import TransactionProposal
from backend.guardrails.transaction_manager import (
    create_transaction,
    validate_transaction,
)
from backend.guardrails.transaction_store import (
    get_transaction,
    save_transaction,
)
from backend.payments.execution_service import PaymentExecutionService
from backend.payments.verification_service import (
    verify_payment_signature,
)
from backend.webhooks.handler import process_payment_webhook
from backend.data.database import initialize_database
from backend.data.persistence import persist_transaction


app = FastAPI(
    title="AgentGuard",
    description="Runtime control plane for bounded AI commerce actions.",
    version="0.1.0",
)

initialize_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


seed_demo_data()


class AgentPurchaseRequest(BaseModel):
    request: str
    authority_id: str
    product_ids: list[str]


class TransactionEvaluationRequest(BaseModel):
    proposal: TransactionProposal
    authority_id: str


class TransactionExecutionRequest(BaseModel):
    transaction_id: str


class PaymentVerificationRequest(BaseModel):
    transaction_id: str
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class TransactionStartRequest(BaseModel):
    proposal: TransactionProposal
    authority_id: str


class TransactionRevalidationRequest(BaseModel):
    transaction_id: str


class ProductPriceUpdateRequest(BaseModel):
    price: int


@app.get("/")
def health_check():
    return {
        "service": "AgentGuard",
        "status": "running",
    }


@app.post("/agent/purchase")
def agent_purchase_endpoint(
    request: AgentPurchaseRequest,
):
    """
    Convert a natural-language purchase request into a guarded
    transaction proposal and authorize it through AgentGuard.

    This endpoint does not execute payment.

    Payment execution remains behind the existing
    /transactions/execute security boundary.
    """

    try:
        return process_purchase_request(
            request=request.request,
            authority_id=request.authority_id,
            product_ids=request.product_ids,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post("/transactions/evaluate")
def evaluate_transaction_endpoint(
    request: TransactionEvaluationRequest,
):
    try:
        authority = get_authority(request.authority_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    try:
        product = get_product(request.proposal.product_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    result = evaluate_transaction(
        proposal=request.proposal,
        authority=authority,
        product=product,
    )

    return {
        "decision": result.decision,
        "reasons": result.reasons,
        "authority_id": authority.authority_id,
        "product_id": product.product_id,
        "current_price": product.price,
    }


@app.post("/transactions/start")
def start_transaction_endpoint(
    request: TransactionStartRequest,
):
    try:
        authority = get_authority(request.authority_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    try:
        product = get_product(request.proposal.product_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    transaction = create_transaction(
        transaction_id=transaction_id,
        authority=authority,
        proposal=request.proposal,
    )

    transaction = validate_transaction(
        transaction=transaction,
        authority=authority,
        product=product,
    )

    persist_transaction(transaction)

    if transaction.state != "AUTHORIZED":
        return {
            "transaction_id": transaction.transaction_id,
            "state": transaction.state,
            "decision": "BLOCK",
            "reasons": [
                "Transaction did not pass initial authorization."
            ],
            "message": "Checkout could not be authorized.",
        }

    return {
        "transaction_id": transaction.transaction_id,
        "state": transaction.state,
        "authority_id": transaction.authority_id,
        "authorized_price": transaction.proposal.amount,
        "current_price": product.price,
        "currency": product.currency,
        "message": (
            "Checkout authorized. Payment has not been executed."
        ),
    }


@app.post("/transactions/execute")
def execute_transaction_endpoint(
    request: TransactionExecutionRequest,
):
    # Load the existing checkout transaction.
    try:
        transaction = get_transaction(request.transaction_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    # Payment can only begin for an authorized checkout.
    if transaction.state != "AUTHORIZED":
        return {
            "transaction_id": transaction.transaction_id,
            "state": transaction.state,
            "message": (
                "Payment cannot be executed because the "
                "transaction is not AUTHORIZED."
            ),
        }

    # Load the authority associated with this transaction.
    try:
        authority = get_authority(transaction.authority_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    # Fetch the CURRENT merchant product state.
    try:
        current_product = get_product(
            transaction.proposal.product_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    # Final server-side revalidation immediately before payment.
    #
    # This is the security boundary.
    # The frontend cannot bypass this check.
    final_result = revalidate_transaction(
        transaction=transaction,
        authority=authority,
        product=current_product,
    )

    if final_result.decision.value != "ALLOW":
        transaction.state = "BLOCKED"
        persistent_transaction(transaction)

        return {
            "transaction_id": transaction.transaction_id,
            "state": transaction.state,
            "decision": final_result.decision,
            "reasons": final_result.reasons,
            "authorized_price": transaction.proposal.amount,
            "current_price": current_product.price,
            "currency": current_product.currency,
            "message": (
                "Final server-side revalidation blocked payment. "
                "Razorpay was not called."
            ),
        }

    # Only an authorized and freshly revalidated transaction
    # is allowed to reach Razorpay.
    payment_service = PaymentExecutionService()

    execution_result = payment_service.execute(transaction)

    persist_transaction(transaction)

    return execution_result


@app.post("/transactions/verify-payment")
def verify_payment_endpoint(
    request: PaymentVerificationRequest,
):
    """
    Verify the Razorpay Checkout success response.

    The server-created Razorpay order ID stored on the transaction
    is the source of truth for signature verification.
    """

    try:
        transaction = get_transaction(
            request.transaction_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    # Payment verification is only valid for a transaction
    # for which AgentGuard already created a Razorpay order.
    if transaction.state != "EXECUTING":
        return {
            "transaction_id": transaction.transaction_id,
            "state": transaction.state,
            "verified": False,
            "message": (
                "Payment verification requires an EXECUTING "
                "transaction."
            ),
        }

    if not transaction.razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Transaction does not have a server-created "
                "Razorpay order."
            ),
        )

    # Never trust the order ID supplied by the browser.
    if (
        request.razorpay_order_id
        != transaction.razorpay_order_id
    ):
        transaction.state = "FAILED"
        persist_transaction(transaction)

        raise HTTPException(
            status_code=400,
            detail=(
                "Razorpay order ID does not match the "
                "server-created order."
            ),
        )

    try:
        verified = verify_payment_signature(
            transaction=transaction,
            payment_id=request.razorpay_payment_id,
            signature=request.razorpay_signature,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not verified:
        transaction.state = "FAILED"
        persist_transaction(transaction)

        return {
            "transaction_id": transaction.transaction_id,
            "state": transaction.state,
            "verified": False,
            "message": (
                "Razorpay signature verification failed. "
                "Payment was not accepted by AgentGuard."
            ),
        }

    # The payment response is authentic.
    transaction.razorpay_payment_id = (
        request.razorpay_payment_id
    )
    transaction.state = "CAPTURED"

    persist_transaction(transaction)

    return {
        "transaction_id": transaction.transaction_id,
        "state": transaction.state,
        "verified": True,
        "razorpay_order_id": transaction.razorpay_order_id,
        "razorpay_payment_id": transaction.razorpay_payment_id,
        "message": (
            "Razorpay payment signature verified. "
            "Transaction marked CAPTURED."
        ),
    }


@app.post("/transactions/revalidate")
def revalidate_transaction_endpoint(
    request: TransactionRevalidationRequest,
):
    try:
        transaction = get_transaction(request.transaction_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    try:
        authority = get_authority(transaction.authority_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    try:
        product = get_product(
            transaction.proposal.product_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    result = revalidate_transaction(
        transaction=transaction,
        authority=authority,
        product=product,
    )

    return {
        "transaction_id": transaction.transaction_id,
        "decision": result.decision,
        "reasons": result.reasons,
        "authorized_price": transaction.proposal.amount,
        "current_price": product.price,
        "currency": product.currency,
    }


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """
    Receive and process Razorpay webhook events.

    The raw request body is used for signature verification.
    The x-razorpay-event-id header is used for idempotency.
    """

    payload = await request.body()

    signature = request.headers.get("X-Razorpay-Signature")
    event_id = request.headers.get("x-razorpay-event-id")
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing X-Razorpay-Signature header.",
        )

    if not event_id:
        raise HTTPException(
            status_code=400,
            detail="Missing x-razorpay-event-id header.",
        )

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_WEBHOOK_SECRET is not configured.",
        )

    try:
        webhook_data = json.loads(
            payload.decode("utf-8")
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        ) from exc

    payment = (
        webhook_data
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    transaction_id = payment.get(
        "notes",
        {},
    ).get("transaction_id")

    if not transaction_id:
        raise HTTPException(
            status_code=400,
            detail="Transaction ID not found in payment notes.",
        )

    try:
        transaction = get_transaction(transaction_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    try:
        transaction, was_duplicate = process_payment_webhook(
            event_id=event_id,
            payload=payload,
            transaction=transaction,
            signature=signature,
            webhook_secret=webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    persist_transaction(transaction)

    return {
        "status": (
            "duplicate"
            if was_duplicate
            else "processed"
        ),
        "transaction_id": transaction.transaction_id,
        "state": transaction.state,
    }


@app.post("/merchant/products/{product_id}/price")
def update_merchant_product_price(
    product_id: str,
    request: ProductPriceUpdateRequest,
):
    try:
        current_product = get_product(product_id)
        old_price = current_product.price

        product = update_product_price(
            product_id=product_id,
            new_price=request.price,
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "product_id": product.product_id,
        "product_name": product.name,
        "old_price": old_price,
        "current_price": product.price,
        "currency": product.currency,
        "message": "Merchant product price updated.",
    }