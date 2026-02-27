"""GCX Credit System — Pre-purchased tokens for simplified UX.

GCX credits are stored per-user in Firestore. Users purchase credits
via Stripe, then spend them per tool call without further payment friction.

Exchange rate: $1 = 20 GCX ($5 = 100 GCX)
Bundles offer volume discounts:
  $5  = 100 GCX  (base rate)
  $20 = 440 GCX  (+10% bonus)
  $50 = 1200 GCX (+20% bonus)
"""

from datetime import datetime, timezone
from google.cloud import firestore

from ..mcp_server.config import config, GCX_PER_DOLLAR

# Firestore client (lazy init)
_db = None

BUNDLES = [
    {"amount_usd": 5, "gcx": 100, "bonus_pct": 0},
    {"amount_usd": 20, "gcx": 440, "bonus_pct": 10},
    {"amount_usd": 50, "gcx": 1200, "bonus_pct": 20},
]


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def get_balance(user_id: str) -> int:
    """Get a user's GCX credit balance."""
    doc = _get_db().collection("gcx_accounts").document(user_id).get()
    if doc.exists:
        return doc.to_dict().get("balance", 0)
    return 0


def add_credits(user_id: str, amount: int, reason: str = "purchase") -> int:
    """Add GCX credits to a user's account. Returns new balance."""
    db = _get_db()
    ref = db.collection("gcx_accounts").document(user_id)

    @firestore.transactional
    def _add(transaction):
        doc = ref.get(transaction=transaction)
        current = doc.to_dict().get("balance", 0) if doc.exists else 0
        new_balance = current + amount
        transaction.set(ref, {
            "balance": new_balance,
            "last_updated": datetime.now(timezone.utc),
        }, merge=True)

        # Log the transaction
        tx_ref = db.collection("gcx_transactions").document()
        transaction.set(tx_ref, {
            "user_id": user_id,
            "type": "credit",
            "amount": amount,
            "reason": reason,
            "balance_after": new_balance,
            "timestamp": datetime.now(timezone.utc),
        })
        return new_balance

    return _add(db.transaction())


def deduct_credits(user_id: str, amount: int, tool_name: str) -> bool:
    """Deduct GCX credits for a tool call. Returns True if successful."""
    db = _get_db()
    ref = db.collection("gcx_accounts").document(user_id)

    @firestore.transactional
    def _deduct(transaction):
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            return False
        current = doc.to_dict().get("balance", 0)
        if current < amount:
            return False
        new_balance = current - amount
        transaction.update(ref, {
            "balance": new_balance,
            "last_updated": datetime.now(timezone.utc),
        })

        # Log the transaction
        tx_ref = db.collection("gcx_transactions").document()
        transaction.set(tx_ref, {
            "user_id": user_id,
            "type": "debit",
            "amount": amount,
            "reason": f"tool:{tool_name}",
            "balance_after": new_balance,
            "timestamp": datetime.now(timezone.utc),
        })
        return True

    return _deduct(db.transaction())


def ensure_account(user_id: str) -> bool:
    """Auto-provision a GCX account if it doesn't exist. Race-safe.

    Uses Firestore create() which raises AlreadyExists if the doc exists,
    preventing race conditions from concurrent requests.

    Returns:
        True if a new account was created, False if it already existed.
    """
    db = _get_db()
    ref = db.collection("gcx_accounts").document(user_id)
    try:
        ref.create({
            "balance": 0,
            "created_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "tier": "free",
            "source": "x402_auto_provision",
        })
        return True
    except Exception:
        # google.cloud.exceptions.Conflict (AlreadyExists) — account exists
        return False


def refund_credits(user_id: str, amount: int, tool_name: str) -> bool:
    """Refund GCX credits when a tool call fails after payment.

    This is the safety net: if dispatch_tool raises an exception after
    credits were deducted, the caller should refund immediately.
    """
    db = _get_db()
    ref = db.collection("gcx_accounts").document(user_id)

    @firestore.transactional
    def _refund(transaction):
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            return False
        current = doc.to_dict().get("balance", 0)
        new_balance = current + amount
        transaction.update(ref, {
            "balance": new_balance,
            "last_updated": datetime.now(timezone.utc),
        })
        tx_ref = db.collection("gcx_transactions").document()
        transaction.set(tx_ref, {
            "user_id": user_id,
            "type": "credit",
            "amount": amount,
            "reason": f"refund:tool_failure:{tool_name}",
            "balance_after": new_balance,
            "timestamp": datetime.now(timezone.utc),
        })
        return True

    return _refund(db.transaction())


def create_account(user_id: str, email: str = "") -> dict:
    """Create a new GCX account."""
    db = _get_db()
    ref = db.collection("gcx_accounts").document(user_id)
    data = {
        "balance": 0,
        "email": email,
        "created_at": datetime.now(timezone.utc),
        "last_updated": datetime.now(timezone.utc),
        "tier": "free",
    }
    ref.set(data, merge=True)
    return data
