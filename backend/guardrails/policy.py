from datetime import datetime, timezone

from .schemas import (
    AuthorityEnvelope,
    MerchantProduct,
    PolicyDecision,
    PolicyResult,
    TransactionProposal,
)


def evaluate_transaction(
    proposal: TransactionProposal,
    authority: AuthorityEnvelope,
    product: MerchantProduct,
) -> PolicyResult:
    """
    Deterministically evaluates whether a proposed transaction
    is within the authority delegated to the AI agent.

    This function does not use an LLM.
    """

    reasons: list[str] = []

    # Check whether the requested action is authorized.
    if proposal.action != authority.allowed_action:
        reasons.append(
            f"Action '{proposal.action.value}' is not authorized."
        )

    # Check merchant binding.
    if proposal.merchant_id != authority.merchant_id:
        reasons.append(
            "Transaction merchant does not match authorized merchant."
        )

    # Check product binding.
    if proposal.product_id != authority.product_id:
        reasons.append(
            "Transaction product does not match authorized product."
        )

    # Check currency.
    if proposal.currency != authority.currency:
        reasons.append(
            "Transaction currency does not match authorized currency."
        )

    # Check spending limit.
    if proposal.amount > authority.max_amount:
        reasons.append(
            f"Transaction amount ₹{proposal.amount} exceeds "
            f"authorized maximum ₹{authority.max_amount}."
        )

    # Check authorization expiry.
    now = datetime.now(timezone.utc)

    if now >= authority.expires_at:
        reasons.append("Authorization has expired.")

    # Revalidate merchant-side product state.
    if product.product_id != proposal.product_id:
        reasons.append(
            "Current merchant product does not match the proposal."
        )

    if product.merchant_id != proposal.merchant_id:
        reasons.append(
            "Current merchant does not match the proposal."
        )

    # Revalidate current price.
    if product.price != proposal.amount:
        reasons.append(
            f"Product price changed: proposed ₹{proposal.amount}, "
            f"current price ₹{product.price}."
        )

    # Check inventory.
    if (
        authority.requires_inventory
        and product.inventory < proposal.quantity
    ):
        reasons.append(
            f"Insufficient inventory: requested {proposal.quantity}, "
            f"available {product.inventory}."
        )

    # Fail closed: any failed check blocks the transaction.
    if reasons:
        return PolicyResult(
            decision=PolicyDecision.BLOCK,
            reasons=reasons,
        )

    return PolicyResult(
        decision=PolicyDecision.ALLOW,
        reasons=["All authorization and merchant-state checks passed."],
    )