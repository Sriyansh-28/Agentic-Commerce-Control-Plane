import pytest

from backend.agent.intent_parser import parse_user_intent


def test_parse_running_shoes_request():
    intent = parse_user_intent(
        "Buy size-9 running shoes under ₹4,000"
    )

    assert intent.request == (
        "Buy size-9 running shoes under ₹4,000"
    )
    assert intent.category == "shoes"
    assert intent.size == 9
    assert intent.max_amount == 4000
    assert intent.currency == "INR"


def test_parse_request_without_size():
    intent = parse_user_intent(
        "Buy running shoes under ₹4,000"
    )

    assert intent.category == "shoes"
    assert intent.size is None
    assert intent.max_amount == 4000


def test_parse_comma_formatted_amount():
    intent = parse_user_intent(
        "Buy shoes below ₹5,000"
    )

    assert intent.max_amount == 5000


def test_empty_request_is_rejected():
    with pytest.raises(
        ValueError,
        match="Shopping request cannot be empty.",
    ):
        parse_user_intent("")


def test_unknown_category_is_rejected():
    with pytest.raises(
        ValueError,
        match="Could not determine the product category",
    ):
        parse_user_intent(
            "Buy a laptop under ₹50,000"
        )


def test_missing_budget_is_rejected():
    with pytest.raises(
        ValueError,
        match="Could not determine the maximum purchase amount",
    ):
        parse_user_intent(
            "Buy size-9 running shoes"
        )