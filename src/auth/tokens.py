"""JWT access token minting, verification, and Bearer token resolution.

Access tokens are HS256 JWTs with the wallet address in the `sub` claim.
This allows stateless validation without a Firestore read on every API call.

Refresh tokens are opaque secrets stored as SHA-256 hashes in Firestore.
"""

import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone

logger = logging.getLogger("studiomcphub.auth")

# Lazy import — jwt may not be installed in all environments
_jwt = None

ACCESS_TOKEN_TTL = 3600       # 1 hour
REFRESH_TOKEN_TTL = 2592000   # 30 days


def _get_jwt():
    global _jwt
    if _jwt is None:
        import jwt as _pyjwt
        _jwt = _pyjwt
    return _jwt


def _get_secret() -> str:
    """Get JWT signing secret from config."""
    from ..mcp_server.config import config
    secret = getattr(config, "jwt_secret", "")
    if not secret:
        import os
        secret = os.getenv("JWT_SECRET", "")
    return secret


def _get_issuer() -> str:
    from ..mcp_server.config import config
    return getattr(config, "oauth_issuer", "https://studiomcphub.com")


def mint_access_token(
    wallet: str,
    client_id: str,
    scope: str = "tools:free tools:paid",
) -> str:
    """Mint a signed JWT access token.

    Args:
        wallet: EVM wallet address (becomes the `sub` claim).
        client_id: OAuth client that requested the token.
        scope: Space-separated scopes granted.

    Returns:
        Encoded JWT string.
    """
    jwt = _get_jwt()
    now = int(time.time())
    payload = {
        "sub": wallet.lower(),
        "client_id": client_id,
        "scope": scope,
        "iss": _get_issuer(),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def verify_access_token(token: str) -> dict | None:
    """Verify and decode a JWT access token.

    Returns:
        Decoded payload dict if valid, None if expired/invalid.
    """
    jwt = _get_jwt()
    secret = _get_secret()
    if not secret:
        return None
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=_get_issuer(),
            options={"require": ["sub", "exp", "iss", "iat"]},
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def resolve_bearer_to_wallet(token: str) -> str | None:
    """Resolve any Bearer token to a wallet address.

    Handles three cases:
      1. Raw wallet address (0x...) — pass through unchanged.
      2. JWT access token — decode and return sub claim.
      3. Unrecognized — return None.

    This is the integration shim that plugs OAuth into the existing
    check_payment() flow without changing payment logic.
    """
    # Case 1: raw wallet address
    if token.startswith("0x") and len(token) == 42:
        try:
            int(token[2:], 16)
            return token.lower()
        except ValueError:
            pass

    # Case 2: JWT
    secret = _get_secret()
    if secret:
        payload = verify_access_token(token)
        if payload and "sub" in payload:
            return payload["sub"]

    # Case 3: unrecognized
    return None


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage (never store raw)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
