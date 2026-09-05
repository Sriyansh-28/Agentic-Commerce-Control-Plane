from backend.guardrails.schemas import (
    ActionType,
    MerchantProduct,
    TransactionProposal,
    UserIntent,
)


def create_purchase_proposal(
    intent: UserIntent,
    product: MerchantProduct,
    quantity: int = 1,
) -> TransactionProposal:
    """
    Convert an authoritative merchant product and validated user intent
    into a purchase proposal.

    The proposal uses the current merchant price as the proposed amount.
    """

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if product.inventory < quantity:
        raise ValueError(
            "Requested quantity exceeds available inventory."
        )

    if product.price > intent.max_amount:
        raise ValueError(
            "Product price exceeds the user's maximum purchase amount."
        )

    if product.currency != intent.currency:
        raise ValueError(
            "Product currency does not match the user's requested currency."
        )

    return TransactionProposal(
        action=ActionType.PURCHASE,
        product_id=product.product_id,
        merchant_id=product.merchant_id,
        amount=product.price,
        currency=product.currency,
        quantity=quantity,
    )