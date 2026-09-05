import os
import re

from dotenv import load_dotenv

from backend.guardrails.schemas import UserIntent


load_dotenv(
    r"E:\Resumes\Razorpay\agentic-commerce-control-plane\.env"
)


def parse_user_intent(request: str) -> UserIntent:
    """
    Convert a natural-language shopping request into UserIntent.

    Gemini is used as the primary language-understanding layer.
    The deterministic parser remains as a fallback.

    IMPORTANT:
    This function only interprets the user's request.
    It does not authorize or execute payments.
    """

    if not request or not request.strip():
        raise ValueError("Shopping request cannot be empty.")

    normalized_request = request.strip()

    if os.getenv("GEMINI_API_KEY"):
        try:
            from backend.agent.llm_client import parse_intent_with_gemini

            return parse_intent_with_gemini(normalized_request)

        except Exception as exc:
            print(
                f"Gemini unavailable, using deterministic fallback: {exc}"
            )

    return _parse_user_intent_deterministically(normalized_request)


def _parse_user_intent_deterministically(
    request: str,
) -> UserIntent:
    """
    Deterministic fallback parser.

    Used only when Gemini is unavailable or fails.
    """

    category = _extract_category(request)
    size = _extract_size(request)
    max_amount = _extract_max_amount(request)

    return UserIntent(
        request=request,
        category=category,
        size=size,
        max_amount=max_amount,
        currency="INR",
    )


def _extract_category(request: str) -> str:
    """
    Extract the product category from the shopping request.
    """

    normalized = request.lower()

    category_patterns = {
        "shoes": [
            r"\brunning shoes?\b",
            r"\bshoes?\b",
            r"\bfootwear\b",
        ],
    }

    for category, patterns in category_patterns.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return category

    raise ValueError(
        "Could not determine the product category from the request."
    )


def _extract_size(request: str) -> int | None:
    """
    Extract an optional numeric product size.
    """

    match = re.search(
        r"\bsize[\s:-]*(\d+)\b",
        request.lower(),
    )

    if match:
        return int(match.group(1))

    return None


def _extract_max_amount(request: str) -> int:
    """
    Extract the maximum allowed purchase amount.

    Supports common deterministic forms such as:
        under ₹4,000
        below ₹4000
        max ₹4,000
        maximum 4000
    """

    patterns = [
        r"(?:under|below|max(?:imum)?|up\s*to)\s*₹?\s*([\d,]+)",
        r"₹\s*([\d,]+)\s*(?:or\s*less|maximum)",
    ]

    for pattern in patterns:
        match = re.search(pattern, request.lower())

        if match:
            amount = match.group(1).replace(",", "")
            return int(amount)

    raise ValueError(
        "Could not determine the maximum purchase amount."
    )