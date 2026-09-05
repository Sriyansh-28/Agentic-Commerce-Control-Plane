from backend.data.catalog_store import get_product
from backend.guardrails.schemas import MerchantProduct, UserIntent


def find_matching_product(
    intent: UserIntent,
    product_ids: list[str],
) -> MerchantProduct:
    """
    Find an authoritative merchant product matching the user's intent.

    Product selection is deterministic and based only on the
    authoritative catalog state.

    The function does not create, modify, or invent products.
    """

    candidates: list[MerchantProduct] = []

    for product_id in product_ids:
        try:
            product = get_product(product_id)
        except KeyError:
            continue

        if product.category.lower() != intent.category.lower():
            continue

        if intent.size is not None:
            if intent.size not in product.available_sizes:
                continue

        if product.inventory <= 0:
            continue

        if product.currency != intent.currency:
            continue

        if product.price > intent.max_amount:
            continue

        candidates.append(product)

    if not candidates:
        raise ValueError(
            "No product matches the requested category, "
            "size, budget, currency, and inventory constraints."
        )

    # Deterministic selection:
    # choose the lowest-priced valid product.
    return min(
        candidates,
        key=lambda product: product.price,
    )