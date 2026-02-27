"""StudioMCPHub OAuth 2.1 authentication module.

Provides MCP-compliant OAuth 2.1 with PKCE, wrapping the existing
wallet-based identity system.
"""

from .tokens import resolve_bearer_to_wallet, verify_access_token
from .oauth import oauth_bp

__all__ = ["resolve_bearer_to_wallet", "verify_access_token", "oauth_bp"]
