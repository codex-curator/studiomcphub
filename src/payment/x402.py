"""x402 Payment Protocol — Agent-native micropayments.

Implements HTTP 402 Payment Required flow for autonomous agents:
1. Agent calls a paid tool endpoint
2. Server returns 402 with payment instructions (wallet, chain, amount)
3. Agent sends USDC on Base L2 to the specified wallet
4. Agent resubmits request with X-PAYMENT header containing tx proof
5. Server verifies payment via x402 facilitator
6. Server executes the tool and returns result

No accounts. No API keys. Payment IS authorization.
"""

import json
import httpx
import structlog
from dataclasses import dataclass

from ..mcp_server.config import config

logger = structlog.get_logger()

# x402 facilitator endpoint (Coinbase CDP)
X402_FACILITATOR_URL = "https://x402.org/facilitator"


@dataclass
class PaymentRequirement:
    """402 Payment Required response payload."""
    tool_name: str
    amount_usd: float
    wallet: str
    chain: str
    token: str

    def to_dict(self) -> dict:
        # Use gokite-aa scheme for Kite chain, exact for Base
        scheme = "gokite-aa" if "kite" in self.chain else "exact"
        # Kite testnet uses settlement token address as asset, Base uses "USDC"
        if "kite" in self.chain:
            from .kite_config import KITE_CHAIN
            asset = KITE_CHAIN.settlement_token
        else:
            asset = "USDC"
        return {
            "x402Version": 1,
            "accepts": [{
                "scheme": scheme,
                "network": self.chain,
                "maxAmountRequired": str(int(self.amount_usd * 1_000_000_000_000_000_000)) if "kite" in self.chain else str(int(self.amount_usd * 1_000_000)),
                "resource": f"tool:{self.tool_name}",
                "description": f"StudioMCPHub: {self.tool_name}",
                "mimeType": "application/json",
                "payTo": self.wallet,
                "maxTimeoutSeconds": 300,
                "asset": asset,
            }],
        }


def extract_wallet(payment_header: str) -> str | None:
    """Extract the sender wallet address from an x402 payment header.

    The X-PAYMENT header is base64-encoded JSON containing payment details.
    Returns the sender/from address, or None if extraction fails.
    """
    import base64
    try:
        decoded = base64.b64decode(payment_header).decode("utf-8")
        data = json.loads(decoded)
        # x402 payment proof contains sender in various possible fields
        return (
            data.get("from")
            or data.get("sender")
            or data.get("payload", {}).get("from")
            or data.get("payload", {}).get("sender")
        )
    except Exception as e:
        logger.warning("Failed to extract wallet from x402 header", error=str(e))
        return None


def create_payment_requirement(tool_name: str, amount_usd: float, network: str = "base") -> PaymentRequirement:
    """Create a 402 payment requirement for a tool call.

    Args:
        tool_name: Name of the paid tool.
        amount_usd: Cost in USD.
        network: Target chain — 'base' (default) or 'kite' (Kite Ozone Testnet).
                 Routed via X-Agent-Network request header.
    """
    from .kite_config import get_network_config

    if network == "kite":
        net = get_network_config("kite")
        return PaymentRequirement(
            tool_name=tool_name,
            amount_usd=amount_usd,
            wallet=config.x402_wallet,  # Same revenue wallet, Kite chain
            chain=net["x402_network"],  # "kite-testnet"
            token="USDT",  # Kite testnet uses Test USDT, not USDC
        )

    return PaymentRequirement(
        tool_name=tool_name,
        amount_usd=amount_usd,
        wallet=config.x402_wallet,
        chain=config.x402_chain,
        token="USDC",
    )


def verify_payment(payment_header: str, expected_amount_usd: float, network: str = "base") -> bool:
    """Verify an x402 payment proof.

    Args:
        payment_header: The X-PAYMENT header value from the client.
        expected_amount_usd: The expected payment amount.

    Returns:
        True if payment is verified, False otherwise.
    """
    try:
        from .kite_config import get_network_config
        net = get_network_config(network)
        facilitator = net["facilitator_url"]

        response = httpx.post(
            f"{facilitator}/verify",
            json={
                "payment": payment_header,
                "payTo": config.x402_wallet,
                "maxAmountRequired": str(int(expected_amount_usd * 1_000_000)),
            },
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("valid", False)
        logger.warning("x402 verification failed", status=response.status_code)
        return False
    except Exception as e:
        logger.error("x402 verification error", error=str(e))
        return False


def settle_payment(payment_header: str) -> dict:
    """Settle an x402 payment (collect funds).

    Called after successful tool execution to finalize the payment.
    """
    try:
        response = httpx.post(
            f"{X402_FACILITATOR_URL}/settle",
            json={"payment": payment_header},
            timeout=30.0,
        )
        return response.json()
    except Exception as e:
        logger.error("x402 settlement error", error=str(e))
        return {"settled": False, "error": str(e)}
