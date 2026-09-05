from ..guardrails.schemas import MerchantProduct

_PRODUCTS: dict[str, MerchantProduct] = {}


def add_product(product: MerchantProduct) -> MerchantProduct:
    """
    Store the authoritative merchant product state.
    """
    _PRODUCTS[product.product_id] = product
    return product


def get_product(product_id: str) -> MerchantProduct:
    """
    Retrieve the current authoritative product state.
    """
    product = _PRODUCTS.get(product_id)

    if product is None:
        raise KeyError(f"Product '{product_id}' was not found.")

    return product

def update_product_price(
    product_id: str,
    new_price: int,
) -> MerchantProduct:
    """
    Update the current merchant price for a product.

    This simulates a merchant changing the price
    while a customer is in the checkout flow.
    """

    product = get_product(product_id)

    if new_price <= 0:
        raise ValueError("Product price must be greater than zero.")

    product.price = new_price

    return product