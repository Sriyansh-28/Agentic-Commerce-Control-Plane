import uuid

from backend.agent.intent_parser import parse_user_intent
from backend.agent.product_matcher import find_matching_product
from backend.agent.proposal_generator import create_purchase_proposal
from backend.data.catalog_store import get_product
from backend.guardrails.authority_store import get_authority
from backend.guardrails.policy import evaluate_transaction
from backend.guardrails.transaction_manager import (
    create_transaction,
    validate_transaction,
)
from backend.guardrails.transaction_store import save_transaction
from backend.data.persistence import persist_transaction

def process_purchase_request(
    request: str,
    authority_id: str,
    product_ids: list[str],
) -> dict:
    """
    Process a natural-language purchase request through AgentGuard.

    The agent-facing layer performs:
        1. Intent parsing
        2. Product matching
        3. Proposal generation
        4. Authority lookup
        5. Deterministic authorization
        6. Transaction persistence

    Payment execution is intentionally NOT performed here.
    """

    # ---------------------------------------------------------
    # 1. Parse the natural-language request
    # ---------------------------------------------------------

    intent = parse_user_intent(request)

    # ---------------------------------------------------------
    # 2. Load the authority envelope
    # ---------------------------------------------------------

    try:
        authority = get_authority(authority_id)
    except KeyError as exc:
        raise ValueError(
            f"Authority '{authority_id}' was not found."
        ) from exc

    # ---------------------------------------------------------
    # 3. Find an authoritative product
    # ---------------------------------------------------------

    product = find_matching_product(
        intent=intent,
        product_ids=product_ids,
    )

    # ---------------------------------------------------------
    # 4. Convert the product into a purchase proposal
    # ---------------------------------------------------------

    proposal = create_purchase_proposal(
        intent=intent,
        product=product,
    )

    # ---------------------------------------------------------
    # 5. Create a transaction
    # ---------------------------------------------------------

    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    transaction = create_transaction(
        transaction_id=transaction_id,
        authority=authority,
        proposal=proposal,
    )

    # ---------------------------------------------------------
    # 6. Deterministic authorization
    # ---------------------------------------------------------

    transaction = validate_transaction(
        transaction=transaction,
        authority=authority,
        product=product,
    )

    persist_transaction(transaction)
    # ---------------------------------------------------------
    # 7. Return a structured agent result
    # ---------------------------------------------------------

    decision = evaluate_transaction(
        proposal=proposal,
        authority=authority,
        product=get_product(proposal.product_id),
    )

    return {
        "transaction_id": transaction.transaction_id,
        "state": transaction.state,
        "decision": decision.decision,
        "reasons": decision.reasons,
        "intent": {
            "request": intent.request,
            "category": intent.category,
            "size": intent.size,
            "max_amount": intent.max_amount,
            "currency": intent.currency,
        },
        "product": {
            "product_id": product.product_id,
            "merchant_id": product.merchant_id,
            "name": product.name,
            "category": product.category,
            "price": product.price,
            "currency": product.currency,
            "available_sizes": product.available_sizes,
            "inventory": product.inventory,
        },
        "proposal": {
            "action": proposal.action,
            "product_id": proposal.product_id,
            "merchant_id": proposal.merchant_id,
            "amount": proposal.amount,
            "currency": proposal.currency,
            "quantity": proposal.quantity,
        },
        "authority": {
            "authority_id": authority.authority_id,
            "agent_id": authority.agent_id,
            "max_amount": authority.max_amount,
            "merchant_id": authority.merchant_id,
        },
        "message": (
            "Agent proposal authorized. "
            "Payment has not been executed."
            if transaction.state == "AUTHORIZED"
            else "Agent proposal was blocked."
        ),
    }