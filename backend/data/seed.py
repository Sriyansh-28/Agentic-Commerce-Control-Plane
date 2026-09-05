from backend.data.catalog_store import add_product
from backend.guardrails.authority_store import create_authority
from backend.guardrails.schemas import MerchantProduct


def seed_demo_data():
    add_product(
        MerchantProduct(
            product_id="shoe_001",
            merchant_id="merchant_001",
            name="Running Shoes",
            category="shoes",
            price=3499,
            currency="INR",
            available_sizes=[8, 9, 10],
            inventory=5,
        )
    )

    create_authority(
        authority_id="auth_001",
        agent_id="agent_001",
        merchant_id="merchant_001",
        product_id="shoe_001",
        max_amount=4000,
    )