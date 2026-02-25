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
        return {
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": self.chain,
                "maxAmountRequired": str(int(self.amount_usd * 1_000_000)),  # USDC has 6 decimals
                "resource": f"tool:{self.tool_name}",
                "description": f"StudioMCPHub: {self.tool_name}",
                "mimeType": "application/json",
                "payTo": self.wallet,
                "maxTimeoutSeconds": 300,
                "asset": "USDC",
            }],
        }


def create_payment_requirement(tool_name: str, amount_usd: float) -> PaymentRequirement:
    """Create a 402 payment requirement for a tool call."""
    return PaymentRequirement(
        tool_name=tool_name,
        amount_usd=amount_usd,
        wallet=config.x402_wallet,
        chain=config.x402_chain,
        token="USDC",
    )


def verify_payment(payment_header: str, expected_amount_usd: float) -> bool:
    """Verify an x402 payment proof.

    Args:
        payment_header: The X-PAYMENT header value from the client.
        expected_amount_usd: The expected payment amount.

    Returns:
        True if payment is verified, False otherwise.
    """
    try:
        response = httpx.post(
            f"{X402_FACILITATOR_URL}/verify",
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
