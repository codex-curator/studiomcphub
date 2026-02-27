"""OAuth consent flow helpers — auth code issuance and exchange.

Manages the authorization code lifecycle:
  1. store_auth_request() — save pending consent params (5-min TTL)
  2. create_auth_code()   — issue a single-use auth code (10-min TTL)
  3. exchange_auth_code() — atomic code→token exchange with PKCE verification
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta

from google.cloud import firestore

from .pkce import verify_challenge
from .tokens import (
    mint_access_token,
    generate_refresh_token,
    hash_refresh_token,
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
)

logger = logging.getLogger("studiomcphub.auth")

_db = None

AUTH_REQUEST_TTL = 300   # 5 minutes
AUTH_CODE_TTL = 600      # 10 minutes


def _get_db():
    global _db
    if _db is None:
        from ..mcp_server.config import config
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def store_auth_request(params: dict) -> str:
    """Store pending authorization request parameters for consent form.

    Args:
        params: Dict with client_id, redirect_uri, state, code_challenge,
                code_challenge_method, scope, resource.

    Returns:
        request_id — used to link the consent form POST back to these params.
    """
    db = _get_db()
    request_id = secrets.token_urlsafe(16)
    db.collection("oauth_auth_requests").document(request_id).set({
        **params,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=AUTH_REQUEST_TTL),
    })
    return request_id


def get_auth_request(request_id: str) -> dict | None:
    """Retrieve a pending auth request (and check expiry)."""
    doc = _get_db().collection("oauth_auth_requests").document(request_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    expires = data.get("expires_at")
    if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return data


def create_auth_code(
    wallet: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    code_challenge: str,
) -> str:
    """Issue a single-use authorization code.

    Args:
        wallet: The wallet address the user entered at consent.
        client_id: The requesting OAuth client.
        redirect_uri: The callback URI to redirect to.
        scope: Granted scopes.
        code_challenge: The S256 PKCE challenge from /authorize.

    Returns:
        The authorization code string.
    """
    db = _get_db()
    code = secrets.token_urlsafe(32)
    db.collection("oauth_auth_codes").document(code).set({
        "code": code,
        "wallet": wallet.lower(),
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge": code_challenge,
        "used": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=AUTH_CODE_TTL),
    })
    return code


def exchange_auth_code(
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
) -> dict | None:
    """Exchange an authorization code for tokens.

    Atomically marks the code as used (single-use enforcement),
    verifies PKCE, and mints access + refresh tokens.

    Args:
        code: The authorization code from /authorize callback.
        code_verifier: The PKCE code_verifier (plaintext).
        redirect_uri: Must match the original redirect_uri.
        client_id: Must match the original client_id.

    Returns:
        Token response dict, or None if exchange fails.
    """
    db = _get_db()
    ref = db.collection("oauth_auth_codes").document(code)

    @firestore.transactional
    def _exchange(transaction):
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            logger.warning("Auth code exchange failed: code not found")
            return None

        data = doc.to_dict()

        # Check single-use
        if data.get("used"):
            logger.warning(f"Auth code replay attempt: {code[:8]}...")
            return None

        # Check expiry
        expires = data.get("expires_at")
        if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            logger.warning("Auth code exchange failed: code expired")
            return None

        # Check client_id match
        if data.get("client_id") != client_id:
            logger.warning("Auth code exchange failed: client_id mismatch")
            return None

        # Check redirect_uri match
        if data.get("redirect_uri") != redirect_uri:
            logger.warning("Auth code exchange failed: redirect_uri mismatch")
            return None

        # Verify PKCE
        if not verify_challenge(code_verifier, data.get("code_challenge", "")):
            logger.warning("Auth code exchange failed: PKCE verification failed")
            return None

        # Mark as used (atomically)
        transaction.update(ref, {"used": True})

        # Mint tokens
        wallet = data["wallet"]
        scope = data.get("scope", "tools:free tools:paid")

        access_token = mint_access_token(wallet, client_id, scope)
        refresh_token = generate_refresh_token()

        # Store refresh token hash
        rt_hash = hash_refresh_token(refresh_token)
        rt_ref = db.collection("oauth_refresh_tokens").document(rt_hash)
        transaction.set(rt_ref, {
            "token_hash": rt_hash,
            "wallet": wallet,
            "client_id": client_id,
            "scope": scope,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_TTL),
            "rotated": False,
        })

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL,
            "refresh_token": refresh_token,
            "scope": scope,
        }

    return _exchange(db.transaction())


def refresh_tokens(
    refresh_token_raw: str,
    client_id: str,
) -> dict | None:
    """Exchange a refresh token for a new access + refresh token pair.

    Implements refresh token rotation — each refresh token is single-use.

    Args:
        refresh_token_raw: The opaque refresh token string.
        client_id: Must match the original client_id.

    Returns:
        New token response dict, or None if refresh fails.
    """
    db = _get_db()
    rt_hash = hash_refresh_token(refresh_token_raw)
    ref = db.collection("oauth_refresh_tokens").document(rt_hash)

    @firestore.transactional
    def _refresh(transaction):
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            logger.warning("Refresh token not found")
            return None

        data = doc.to_dict()

        # Check rotation (single-use)
        if data.get("rotated"):
            logger.warning("Refresh token replay — possible token theft")
            return None

        # Check expiry
        expires = data.get("expires_at")
        if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            logger.warning("Refresh token expired")
            return None

        # Check client_id
        if data.get("client_id") != client_id:
            logger.warning("Refresh token client_id mismatch")
            return None

        # Rotate: mark old token as used
        transaction.update(ref, {"rotated": True})

        # Mint new tokens
        wallet = data["wallet"]
        scope = data.get("scope", "tools:free tools:paid")

        new_access = mint_access_token(wallet, client_id, scope)
        new_refresh = generate_refresh_token()

        # Store new refresh token
        new_hash = hash_refresh_token(new_refresh)
        new_ref = db.collection("oauth_refresh_tokens").document(new_hash)
        transaction.set(new_ref, {
            "token_hash": new_hash,
            "wallet": wallet,
            "client_id": client_id,
            "scope": scope,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_TTL),
            "rotated": False,
        })

        return {
            "access_token": new_access,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL,
            "refresh_token": new_refresh,
            "scope": scope,
        }

    return _refresh(db.transaction())
