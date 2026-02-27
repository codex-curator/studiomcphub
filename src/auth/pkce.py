"""PKCE (Proof Key for Code Exchange) — S256 verification.

Implements RFC 7636 S256 code challenge method as required by the
MCP OAuth 2.1 specification (Nov 2025).
"""

import base64
import hashlib
import hmac


def verify_challenge(code_verifier: str, code_challenge: str) -> bool:
    """Verify a PKCE S256 code challenge against the verifier.

    Args:
        code_verifier: The original random string (43-128 chars, unreserved chars).
        code_challenge: The base64url(SHA256(code_verifier)) sent in /authorize.

    Returns:
        True if the verifier matches the challenge.
    """
    if not code_verifier or not code_challenge:
        return False
    computed = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(computed, code_challenge)
