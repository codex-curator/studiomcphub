"""Agent Volume Discount Tiers — 30-day rolling spend tracking.

Tracks per-wallet spend over a rolling 30-day window and applies
automatic volume discounts:
  Standard ($0-49):   0% discount
  Active   ($50-99):  10% discount
  Pro      ($100-199): 20% discount
  Studio   ($200+):   30% discount
"""

from datetime import datetime, timedelta, timezone
from google.cloud import firestore

from ..mcp_server.config import config, AGENT_VOLUME_TIERS

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def record_spend(wallet: str, amount_usd: float, tool_name: str) -> None:
    """Record a spend event for tier tracking."""
    db = _get_db()
    db.collection("agent_spend").add({
        "wallet": wallet.lower(),
        "amount_usd": amount_usd,
        "tool": tool_name,
        "timestamp": datetime.now(timezone.utc),
    })


def get_30day_spend(wallet: str) -> float:
    """Get total spend for a wallet in the last 30 days."""
    try:
        db = _get_db()
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        docs = (
            db.collection("agent_spend")
            .where("wallet", "==", wallet.lower())
            .where("timestamp", ">=", cutoff)
            .stream()
        )
        return sum(doc.to_dict().get("amount_usd", 0) for doc in docs)
    except Exception:
        # Index may still be building, or collection empty
        return 0.0


def get_tier(wallet: str) -> dict:
    """Get the current volume tier for a wallet."""
    spend = get_30day_spend(wallet)
    current = AGENT_VOLUME_TIERS[0]
    for tier in AGENT_VOLUME_TIERS:
        if spend >= tier["min_spend_usd"]:
            current = tier

    # Calculate next tier threshold
    next_tier_at = None
    for tier in AGENT_VOLUME_TIERS:
        if tier["min_spend_usd"] > spend:
            next_tier_at = tier["min_spend_usd"]
            break

    return {
        "label": current["label"],
        "discount_pct": current["discount_pct"],
        "spend_30d": round(spend, 2),
        "next_tier_at": next_tier_at,
    }


def apply_discount(wallet: str, base_usd: float) -> tuple[float, dict]:
    """Apply volume discount to a base price.

    Returns:
        (discounted_usd, tier_info)
    """
    tier = get_tier(wallet)
    discount = tier["discount_pct"] / 100
    discounted = round(base_usd * (1 - discount), 6)
    return discounted, tier
