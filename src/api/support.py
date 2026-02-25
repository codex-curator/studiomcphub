"""Support & Feedback — Ticket system for bugs, credits, and feature requests.

Accessible to both agents (API) and humans (web form).
Tickets stored in Firestore, optionally linked to wallet address.
"""

from datetime import datetime, timezone
from google.cloud import firestore

from ..mcp_server.config import config

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


TICKET_TYPES = [
    "bug",              # Something broke
    "credit_issue",     # Payment went through but credits not applied
    "feature_request",  # Suggest a new tool or improvement
    "feedback",         # General feedback
    "compliance",       # Copyright or content concern
    "enterprise",       # Enterprise inquiry
]


def create_ticket(
    ticket_type: str,
    subject: str,
    description: str,
    wallet_address: str | None = None,
    email: str | None = None,
    tool_name: str | None = None,
    tx_hash: str | None = None,
) -> dict:
    """Create a support ticket.

    Args:
        ticket_type: One of TICKET_TYPES.
        subject: Short summary.
        description: Full details.
        wallet_address: Optional wallet for identity/lookup.
        email: Optional email for human follow-up.
        tool_name: Which tool was involved (if applicable).
        tx_hash: Transaction hash for payment issues.

    Returns:
        dict with ticket_id, status, created_at.
    """
    if ticket_type not in TICKET_TYPES:
        raise ValueError(f"Invalid ticket type. Must be one of: {TICKET_TYPES}")

    db = _get_db()
    ref = db.collection("support_tickets").document()
    now = datetime.now(timezone.utc)

    ticket = {
        "ticket_id": ref.id,
        "type": ticket_type,
        "subject": subject,
        "description": description,
        "status": "open",
        "priority": "high" if ticket_type in ("credit_issue", "compliance") else "normal",
        "wallet": wallet_address.lower() if wallet_address else None,
        "email": email,
        "tool": tool_name,
        "tx_hash": tx_hash,
        "created_at": now,
        "updated_at": now,
        "resolution": None,
    }

    ref.set(ticket)

    return {
        "ticket_id": ref.id,
        "status": "open",
        "priority": ticket["priority"],
        "created_at": now.isoformat(),
        "message": "Ticket created. We'll respond within 24 hours.",
    }


def get_ticket(ticket_id: str) -> dict | None:
    """Get a ticket by ID."""
    db = _get_db()
    doc = db.collection("support_tickets").document(ticket_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


def get_tickets_by_wallet(wallet_address: str, limit: int = 20) -> list[dict]:
    """Get all tickets for a wallet address."""
    db = _get_db()
    docs = (
        db.collection("support_tickets")
        .where("wallet", "==", wallet_address.lower())
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]
