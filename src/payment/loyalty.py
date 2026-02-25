"""Loyalty Rewards — 5% credit-back on every paid tool call.

Like a frequent flyer program for AI agents. Credits accrue per wallet,
are NOT deposited into the wallet (no on-chain cost), and can be redeemed
for any tool call at any time.

Architecture:
  - Every paid tool call earns 5% of the GCX cost back as loyalty credits
  - Credits stored in Firestore per wallet address (off-chain)
  - Redeemable for any tool, any time — no expiration
  - Works for both agent wallets and human accounts
  - Credits are non-transferable (tied to wallet)

Example:
  Agent spends 8 GCX on generate_image → earns 0.4 loyalty credits
  After 25 generations (200 GCX spent) → 10 loyalty credits = 1 free pipeline
  After 100 generations (800 GCX spent) → 40 credits = 5 free pipelines

This incentivizes repeat usage and rewards loyalty without creating an
exploitable discount loop — the 5% only applies to actual paid calls,
not to loyalty-redeemed calls.
"""

from datetime import datetime, timezone
from google.cloud import firestore

from ..mcp_server.config import config

LOYALTY_RATE = 0.05  # 5% credit-back

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def earn_loyalty(wallet_address: str, gcx_spent: int, tool_name: str) -> float:
    """Record loyalty credits earned from a paid tool call.

    Only called on actual paid calls — NOT on loyalty redemptions,
    preventing infinite credit loops.

    Args:
        wallet_address: EVM wallet address (identity).
        gcx_spent: GCX tokens spent on this call.
        tool_name: Which tool was called.

    Returns:
        Credits earned (float, can be fractional).
    """
    if gcx_spent <= 0:
        return 0.0

    credits_earned = gcx_spent * LOYALTY_RATE
    db = _get_db()
    ref = db.collection("loyalty_accounts").document(wallet_address.lower())

    @firestore.transactional
    def _accrue(transaction):
        doc = ref.get(transaction=transaction)
        current = doc.to_dict() if doc.exists else {"balance": 0.0, "lifetime_earned": 0.0, "lifetime_spent_gcx": 0}

        new_balance = current.get("balance", 0.0) + credits_earned
        new_lifetime = current.get("lifetime_earned", 0.0) + credits_earned
        new_spent = current.get("lifetime_spent_gcx", 0) + gcx_spent

        transaction.set(ref, {
            "balance": new_balance,
            "lifetime_earned": new_lifetime,
            "lifetime_spent_gcx": new_spent,
            "last_earned_at": datetime.now(timezone.utc),
            "wallet": wallet_address.lower(),
        }, merge=True)

        # Log the earn event
        log_ref = db.collection("loyalty_events").document()
        transaction.set(log_ref, {
            "wallet": wallet_address.lower(),
            "type": "earn",
            "credits": credits_earned,
            "gcx_spent": gcx_spent,
            "tool": tool_name,
            "timestamp": datetime.now(timezone.utc),
        })

        return new_balance

    new_balance = _accrue(db.transaction())
    return credits_earned


def get_loyalty_balance(wallet_address: str) -> dict:
    """Get a wallet's loyalty credit balance and stats.

    Returns:
        dict with balance, lifetime_earned, lifetime_spent_gcx.
    """
    db = _get_db()
    doc = db.collection("loyalty_accounts").document(wallet_address.lower()).get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "balance": data.get("balance", 0.0),
            "lifetime_earned": data.get("lifetime_earned", 0.0),
            "lifetime_spent_gcx": data.get("lifetime_spent_gcx", 0),
        }
    return {"balance": 0.0, "lifetime_earned": 0.0, "lifetime_spent_gcx": 0}


def redeem_loyalty(wallet_address: str, credits_to_redeem: float, tool_name: str) -> bool:
    """Redeem loyalty credits for a tool call.

    Redeemed calls do NOT earn additional loyalty credits (prevents loops).

    Args:
        wallet_address: EVM wallet address.
        credits_to_redeem: How many loyalty credits to use.
        tool_name: Which tool is being called.

    Returns:
        True if redemption succeeded, False if insufficient balance.
    """
    db = _get_db()
    ref = db.collection("loyalty_accounts").document(wallet_address.lower())

    @firestore.transactional
    def _redeem(transaction):
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            return False

        current_balance = doc.to_dict().get("balance", 0.0)
        if current_balance < credits_to_redeem:
            return False

        transaction.update(ref, {
            "balance": current_balance - credits_to_redeem,
            "last_redeemed_at": datetime.now(timezone.utc),
        })

        # Log the redemption
        log_ref = db.collection("loyalty_events").document()
        transaction.set(log_ref, {
            "wallet": wallet_address.lower(),
            "type": "redeem",
            "credits": credits_to_redeem,
            "tool": tool_name,
            "timestamp": datetime.now(timezone.utc),
        })

        return True

    return _redeem(db.transaction())


def can_redeem_for_tool(wallet_address: str, gcx_cost: int) -> bool:
    """Check if wallet has enough loyalty credits to cover a tool call.

    Loyalty credits map 1:1 to GCX (1 loyalty credit = 1 GCX equivalent).
    """
    balance = get_loyalty_balance(wallet_address)
    return balance["balance"] >= gcx_cost
