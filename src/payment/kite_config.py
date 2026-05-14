"""Kite AI Chain Configuration — AP2 x402 payment support.

Extends StudioMCPHub's x402 payment infrastructure to support Kite chain
alongside existing Base L2. Agents route payments via X-Agent-Network header:
  - X-Agent-Network: kite   → settle on Kite Ozone Testnet (chain 2368)
  - X-Agent-Network: base   → settle on Base L2 (default, existing behavior)
  - (no header)              → default to Base L2

Kite-native vocabulary:
  - AP2: Agent Payments Protocol (Kite's x402 implementation)
  - SPACE Framework: Root → Delegated → Session key hierarchy
  - Standing Intent: Budget constraint set by Root Authority
  - ClientAgentVault: AA SDK smart account per agent
  - Facilitator: Middleware for x402 verification + settlement
  - PoAI: Proof of Attributed Intelligence (rewards AI compute)
"""

from dataclasses import dataclass, field


@dataclass
class KiteChainConfig:
    """Kite chain parameters (from docs.gokite.ai)."""
    # Testnet
    testnet_chain_id: int = 2368
    testnet_rpc_url: str = "https://rpc-testnet.gokite.ai/"
    testnet_explorer_url: str = "https://testnet.kitescan.ai"
    testnet_faucet_url: str = "https://faucet.gokite.ai"
    # Mainnet
    mainnet_chain_id: int = 2366
    mainnet_rpc_url: str = "https://rpc.gokite.ai/"
    mainnet_rpc_fallback: str = "https://rpc-virginia.gokite.ai"
    mainnet_ws_url: str = "wss://rpc.gokite.ai/ws"
    mainnet_explorer_url: str = "https://kitescan.ai"
    # Common
    chain_name: str = "KiteAI"
    currency_symbol: str = "KITE"
    # Settlement token on testnet (Test USDT)
    settlement_token: str = "0x0fF5393387ad2f9f691FD6Fd28e07E3969e27e63"
    # Pieverse x402 Facilitator (recommended by Kite docs)
    facilitator_url: str = "https://facilitator.pieverse.io"
    facilitator_address: str = "0x12343e649e6b2b2b77649DFAb88f103c02F3C78b"
    # x402 scheme
    x402_scheme: str = "gokite-aa"
    x402_network: str = "kite-testnet"
    # AA SDK contracts (testnet)
    settlement_contract: str = "0x8d9FaD78d5Ce247aA01C140798B9558fd64a63E3"
    client_agent_vault_impl: str = "0xB5AAFCC6DD4DFc2B80fb8BCcf406E1a2Fd559e23"
    gokite_account_factory: str = "0xF0Fc19F0dc393867F19351d25EDfc5E099561cb7"
    service_registry: str = "0xc67a4AbcD8853221F241a041ACb1117b38DA587F"
    # Kite Passport MCP endpoint
    passport_mcp_url: str = "https://neo.dev.gokite.ai/v1/mcp"


@dataclass
class AgentPassportConfig:
    """Kite Agent Passport configuration stubs.

    Each agent in the RAMS gets a Kite Passport (on-chain identity)
    linked to a ClientAgentVault (ERC-4337 smart account).
    """
    # Thalos Prime — Architect Agent (root of the RAMS)
    thalos_passport_id: str = ""  # Set after Kite SDK registration
    thalos_vault_address: str = ""

    # StudioMCPHub — External MCP Service Provider
    studio_passport_id: str = ""
    studio_vault_address: str = ""


@dataclass
class SessionKeyConfig:
    """Ephemeral session key configuration for per-job authorization.

    In the SPACE Framework:
    - Root Authority (Ash Multisig) → deploys Standing Intent
    - Standing Intent → authorizes Thalos Prime with daily budget
    - Thalos Prime → creates Session Keys scoped to one pipeline job
    - Session Key → authorizes payments to worker agents for that job only
    """
    # Maximum duration for a session key (seconds)
    max_ttl_seconds: int = 3600  # 1 hour per pipeline job
    # Maximum USDC a single session key can authorize
    max_spend_usdc: float = 1.0  # Well above single-job cost ($0.448)
    # Scoped permissions
    allowed_operations: list = field(default_factory=lambda: [
        "x402_payment",
        "eas_attestation",
        "mcp_tool_call",
    ])


# Singleton instances
KITE_CHAIN = KiteChainConfig()
AGENT_PASSPORTS = AgentPassportConfig()
SESSION_KEY_DEFAULTS = SessionKeyConfig()


def get_network_config(network: str) -> dict:
    """Return chain configuration based on network header value.

    Args:
        network: Value from X-Agent-Network header ('kite' or 'base')

    Returns:
        Dict with chain_id, rpc_url, facilitator_url, settlement_token, etc.
    """
    if network == "kite":
        return {
            "chain_id": KITE_CHAIN.testnet_chain_id,
            "chain_name": KITE_CHAIN.chain_name,
            "rpc_url": KITE_CHAIN.testnet_rpc_url,
            "facilitator_url": KITE_CHAIN.facilitator_url,
            "settlement_token": KITE_CHAIN.settlement_token,
            "explorer_url": KITE_CHAIN.testnet_explorer_url,
            "x402_scheme": KITE_CHAIN.x402_scheme,
            "x402_network": KITE_CHAIN.x402_network,
        }
    # Default: Base L2
    return {
        "chain_id": 8453,
        "chain_name": "Base",
        "rpc_url": "https://mainnet.base.org",
        "facilitator_url": "https://x402.org/facilitator",
        "settlement_token": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "explorer_url": "https://basescan.org",
        "x402_scheme": "exact",
        "x402_network": "base",
    }


def generate_session_key_stub(job_id: str, budget_usdc: float) -> dict:
    """Generate a session key authorization stub for a pipeline job.

    This is a placeholder until the Kite AA SDK is integrated.
    In production, this would call the Kite SDK to create an
    on-chain session key scoped to the specific job.

    Args:
        job_id: The pipeline job identifier
        budget_usdc: Maximum USDC this session can spend

    Returns:
        Session key metadata (stub — not yet on-chain)
    """
    return {
        "job_id": job_id,
        "budget_usdc": min(budget_usdc, SESSION_KEY_DEFAULTS.max_spend_usdc),
        "ttl_seconds": SESSION_KEY_DEFAULTS.max_ttl_seconds,
        "allowed_operations": SESSION_KEY_DEFAULTS.allowed_operations,
        "status": "stub",  # Will be "active" once Kite SDK is integrated
        "note": "Session key generation requires Kite AA SDK integration",
    }
