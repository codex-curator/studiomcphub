"""OAuth client registry — Firestore-backed.

Manages registered MCP clients (Claude.ai, Claude Desktop, DCR clients).
Pre-seeds trusted clients on first startup.
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from google.cloud import firestore

logger = logging.getLogger("studiomcphub.auth")

_db = None
_COLLECTION = "oauth_clients"

# Pre-seeded trusted clients — auto-approved consent, no warning banner.
TRUSTED_CLIENTS = [
    {
        "client_id": "claude-ai",
        "client_name": "Claude.ai",
        "redirect_uris": [
            "https://claude.ai/api/mcp/auth_callback",
            "https://claude.com/api/mcp/auth_callback",
        ],
        "grant_types": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": "none",
        "scope": "tools:free tools:paid account:read",
        "is_trusted": True,
    },
    {
        "client_id": "claude-desktop",
        "client_name": "Claude Desktop",
        "redirect_uris": [
            "https://claude.ai/api/mcp/auth_callback",
            "https://claude.com/api/mcp/auth_callback",
        ],
        "grant_types": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": "none",
        "scope": "tools:free tools:paid account:read",
        "is_trusted": True,
    },
]


def _get_db():
    global _db
    if _db is None:
        from ..mcp_server.config import config
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def get_client(client_id: str) -> dict | None:
    """Look up a registered OAuth client by ID."""
    doc = _get_db().collection(_COLLECTION).document(client_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


def validate_redirect_uri(client: dict, redirect_uri: str) -> bool:
    """Check if a redirect URI is registered for this client."""
    registered = client.get("redirect_uris", [])
    # Exact match for HTTPS URIs
    if redirect_uri in registered:
        return True
    # Allow localhost with any port for local dev
    for uri in registered:
        if uri.startswith("http://localhost:") and redirect_uri.startswith("http://localhost:"):
            return True
    return False


def register_client(data: dict) -> dict:
    """Register a new OAuth client via Dynamic Client Registration (RFC 7591).

    Args:
        data: Client metadata from the registration request.

    Returns:
        Full client document including generated client_id.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    redirect_uris = data.get("redirect_uris", [])
    if not redirect_uris:
        raise ValueError("redirect_uris is required")

    # Validate redirect URIs: must be https:// or http://localhost
    for uri in redirect_uris:
        if not (uri.startswith("https://") or uri.startswith("http://localhost")):
            raise ValueError(f"Invalid redirect_uri: {uri} (must be https:// or http://localhost)")

    client_id = str(uuid.uuid4())
    registration_access_token = secrets.token_urlsafe(32)

    grant_types = data.get("grant_types", ["authorization_code", "refresh_token"])
    allowed_grants = {"authorization_code", "refresh_token"}
    if not set(grant_types).issubset(allowed_grants):
        raise ValueError(f"Unsupported grant_types: {set(grant_types) - allowed_grants}")

    client_doc = {
        "client_id": client_id,
        "client_name": data.get("client_name", f"MCP Client {client_id[:8]}"),
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "token_endpoint_auth_method": data.get("token_endpoint_auth_method", "none"),
        "scope": data.get("scope", "tools:free tools:paid"),
        "is_trusted": False,
        "created_at": datetime.now(timezone.utc),
        "registration_access_token": registration_access_token,
    }

    _get_db().collection(_COLLECTION).document(client_id).set(client_doc)
    logger.info(f"Registered new OAuth client: {client_doc['client_name']} ({client_id})")

    # Return response (RFC 7591 format)
    return {
        "client_id": client_id,
        "client_secret": None,
        "client_id_issued_at": int(datetime.now(timezone.utc).timestamp()),
        "client_name": client_doc["client_name"],
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "token_endpoint_auth_method": "none",
        "registration_access_token": registration_access_token,
        "registration_client_uri": f"https://studiomcphub.com/register/{client_id}",
    }


def ensure_trusted_clients():
    """Idempotently seed trusted clients into Firestore.

    Called once at startup. Uses create() to avoid overwriting
    existing clients (race-safe).
    """
    db = _get_db()
    for client in TRUSTED_CLIENTS:
        ref = db.collection(_COLLECTION).document(client["client_id"])
        try:
            ref.create({
                **client,
                "created_at": datetime.now(timezone.utc),
                "registration_access_token": None,
            })
            logger.info(f"Seeded trusted OAuth client: {client['client_name']}")
        except Exception:
            # AlreadyExists — client already seeded, skip
            pass
