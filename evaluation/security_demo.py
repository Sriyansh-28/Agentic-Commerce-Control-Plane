from datetime import datetime, timedelta, timezone

from backend.guardrails.policy import evaluate_transaction, PolicyDecision
from backend.guardrails.schemas import (
    ActionType,
    AuthorityEnvelope,
    MerchantProduct,
    TransactionProposal,
)
from backend.guardrails.transaction import TransactionState
from backend.guardrails.transaction_manager import execute_transaction


def authority(
    max_amount=4000,
    merchant_id="merchant_001",
    product_id="shoe_001",
    expires_at=None,
):
    return AuthorityEnvelope(
        authority_id="auth_demo",
        agent_id="agent_001",
        allowed_action=ActionType.PURCHASE,
        merchant_id=merchant_id,
        product_id=product_id,
        max_amount=max_amount,
        currency="INR",
        requires_inventory=True,
        requires_price_revalidation=True,
        expires_at=expires_at
        or datetime.now(timezone.utc) + timedelta(hours=1),
    )


def product(
    price=3499,
    inventory=5,
    merchant_id="merchant_001",
    product_id="shoe_001",
):
    return MerchantProduct(
        product_id=product_id,
        merchant_id=merchant_id,
        name="Running Shoes",
        category="shoes",
        price=price,
        currency="INR",
        available_sizes=[8, 9, 10],
        inventory=inventory,
    )


def proposal(
    amount=3499,
    merchant_id="merchant_001",
    product_id="shoe_001",
):
    return TransactionProposal(
        action=ActionType.PURCHASE,
        product_id=product_id,
        merchant_id=merchant_id,
        amount=amount,
        currency="INR",
        quantity=1,
    )


def run_scenario(name, authority_obj, product_obj, proposal_obj):
    result = evaluate_transaction(
        proposal=proposal_obj,
        authority=authority_obj,
        product=product_obj,
    )

    status = "PASS" if result.decision == PolicyDecision.ALLOW else "BLOCKED"

    print(f"[{status}] {name}")
    print(f"       Decision: {result.decision.value}")

    if result.reasons:
        for reason in result.reasons:
            print(f"       Reason: {reason}")

    print()

    return result


def main():
    print("=" * 70)
    print("AGENTGUARD SECURITY EVALUATION")
    print("=" * 70)
    print()

    # 1. Normal purchase
    run_scenario(
        "Valid purchase within delegated authority",
        authority(),
        product(price=3499),
        proposal(amount=3499),
    )

    # 2. Merchant changes price after agent selection
    run_scenario(
        "Merchant price changes from ₹3,499 to ₹4,799",
        authority(),
        product(price=4799),
        proposal(amount=3499),
    )

    # 3. Agent attempts to exceed delegated amount
    run_scenario(
        "Agent proposes ₹5,000 against ₹4,000 authority",
        authority(max_amount=4000),
        product(price=5000),
        proposal(amount=5000),
    )

    # 4. Wrong merchant
    run_scenario(
        "Agent attempts purchase from unauthorized merchant",
        authority(merchant_id="merchant_001"),
        product(merchant_id="merchant_002"),
        proposal(merchant_id="merchant_002"),
    )

    # 5. Wrong product
    run_scenario(
        "Agent attempts purchase of unauthorized product",
        authority(product_id="shoe_001"),
        product(product_id="laptop_001"),
        proposal(product_id="laptop_001"),
    )

    # 6. Inventory disappears
    run_scenario(
        "Product becomes unavailable before payment",
        authority(),
        product(price=3499, inventory=0),
        proposal(amount=3499),
    )

    # 7. Authority expires
    run_scenario(
        "Delegated authority has expired",
        authority(
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
        ),
        product(price=3499),
        proposal(amount=3499),
    )

    # 8. State-machine protection
    print("[BLOCKED] Unauthorized transaction reaches payment execution")

    from backend.guardrails.schemas import Transaction

    transaction = Transaction(
        transaction_id="txn_security_demo",
        authority_id="auth_demo",
        proposal=proposal(),
        state=TransactionState.BLOCKED.value,
    )

    try:
        execute_transaction(transaction)
        print("       ERROR: unauthorized execution was allowed")
    except ValueError as exc:
        print(f"       Reason: {exc}")

    print()
    print("=" * 70)
    print("SECURITY EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()