"""StudioMCPHub configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class ToolPricing:
    """Per-call pricing in USD cents."""
    x402_cents: int     # x402 USDC price (cents)
    stripe_cents: int   # Stripe price (cents)
    gcx_credits: int    # GCX credit cost


# Tool pricing table
PRICING = {
    "generate_image":    ToolPricing(x402_cents=8,  stripe_cents=10, gcx_credits=10),
    "upscale_image":     ToolPricing(x402_cents=4,  stripe_cents=5,  gcx_credits=5),
    "enrich_metadata":   ToolPricing(x402_cents=3,  stripe_cents=4,  gcx_credits=4),
    "infuse_metadata":   ToolPricing(x402_cents=1,  stripe_cents=2,  gcx_credits=2),
    "register_hash":     ToolPricing(x402_cents=1,  stripe_cents=2,  gcx_credits=2),
    "store_permanent":   ToolPricing(x402_cents=5,  stripe_cents=6,  gcx_credits=6),
    "mint_nft":          ToolPricing(x402_cents=10, stripe_cents=12, gcx_credits=12),
    "verify_provenance": ToolPricing(x402_cents=0,  stripe_cents=0,  gcx_credits=0),
    "full_pipeline":     ToolPricing(x402_cents=25, stripe_cents=30, gcx_credits=30),
}

# GCX exchange rate
GCX_PER_DOLLAR = 20  # $1 = 20 GCX, $5 = 100 GCX


@dataclass
class Config:
    """Server configuration from environment."""

    # GCP
    gcp_project: str = os.getenv("GCP_PROJECT", "the-golden-codex-1111")
    gcp_region: str = os.getenv("GCP_REGION", "us-west1")

    # Firestore
    firestore_database: str = os.getenv("FIRESTORE_DATABASE", "golden-codex-database")

    # Backend service URLs (Golden Codex pipeline agents)
    sd35_url: str = os.getenv("SD35_SERVICE_URL", "https://sd35-l4-172867820131.us-east4.run.app")
    esrgan_url: str = os.getenv("ESRGAN_SERVICE_URL", "https://esrgan-gpu-primary-172867820131.us-central1.run.app")
    nova_url: str = os.getenv("NOVA_SERVICE_URL", "https://nova-agent-172867820131.us-west1.run.app")
    atlas_url: str = os.getenv("ATLAS_SERVICE_URL", "https://atlas-agent-172867820131.us-west1.run.app")
    archivus_url: str = os.getenv("ARCHIVUS_SERVICE_URL", "https://archivus-agent-172867820131.us-west1.run.app")
    mintra_url: str = os.getenv("MINTRA_SERVICE_URL", "https://mintra-agent-172867820131.us-west1.run.app")

    # Storage
    archive_bucket: str = os.getenv("ARCHIVE_BUCKET", "codex-archive-bucket")
    intake_bucket: str = os.getenv("INTAKE_BUCKET", "codex-intake-bucket")

    # x402 payment
    x402_wallet: str = os.getenv("X402_WALLET", "0xFE141943a93c184606F3060103D975662327063B")
    x402_chain: str = os.getenv("X402_CHAIN", "base")  # Base L2

    # Stripe
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")

    # Server
    port: int = int(os.getenv("PORT", "8080"))
    host: str = os.getenv("HOST", "0.0.0.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # MCP Server metadata
    server_name: str = "StudioMCPHub"
    server_version: str = "0.1.0"
    server_description: str = (
        "Creative AI tools for autonomous agents. "
        "Image generation, upscaling, metadata enrichment, "
        "provenance registration, permanent storage, and NFT minting."
    )


config = Config()
