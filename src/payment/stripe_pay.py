"""Stripe per-call payment integration.

For users who prefer traditional payment rails. Creates a PaymentIntent
per tool call, or charges against a saved payment method.
"""

import stripe
import structlog
from datetime import datetime, timezone

from ..mcp_server.config import config

logger = structlog.get_logger()

stripe.api_key = config.stripe_secret_key


def create_payment_intent(
    tool_name: str,
    amount_cents: int,
    customer_id: str | None = None,
) -> dict:
    """Create a Stripe PaymentIntent for a tool call.

    Args:
        tool_name: The tool being called.
        amount_cents: Price in USD cents.
        customer_id: Optional Stripe customer ID for saved payment methods.

    Returns:
        dict with client_secret, payment_intent_id.
    """
    params = {
        "amount": amount_cents,
        "currency": "usd",
        "metadata": {
            "tool": tool_name,
            "service": "studiomcphub",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "automatic_payment_methods": {"enabled": True},
    }
    if customer_id:
        params["customer"] = customer_id

    intent = stripe.PaymentIntent.create(**params)
    logger.info("stripe_intent_created", tool=tool_name, amount=amount_cents)

    return {
        "client_secret": intent.client_secret,
        "payment_intent_id": intent.id,
        "amount_cents": amount_cents,
    }


def verify_payment_intent(payment_intent_id: str) -> bool:
    """Verify a Stripe PaymentIntent has succeeded."""
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return intent.status == "succeeded"
    except stripe.error.StripeError as e:
        logger.error("stripe_verify_failed", error=str(e))
        return False
