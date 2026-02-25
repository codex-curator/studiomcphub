"""
StudioMCPHub — MCP Server for Creative AI Tools

Built by AI, for AI. Exposes the Golden Codex pipeline as discoverable,
pay-per-call MCP tools via Streamable HTTP transport.

Tools offered:
  - generate_image:    SD 3.5 Large + T5-XXL text-to-image
  - upscale_image:     ESRGAN x4 super-resolution (NVIDIA L4 GPU)
  - enrich_metadata:   Nova AI analysis (Gemini 2.5/3.0 Pro)
  - infuse_metadata:   Atlas XMP/IPTC/C2PA metadata embedding
  - register_hash:     Aegis perceptual hash + LSH index registration
  - store_permanent:   Archivus Arweave L1 permanent storage
  - mint_nft:          Mintra Polygon NFT minting
  - verify_provenance: Aegis strip-proof provenance verification (FREE)
  - full_pipeline:     Complete creative pipeline in one call

Payment methods: x402 (USDC/Base), Stripe, GCX Credits
"""

import json
import logging
import base64
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from mcp import types as mcp_types

from .config import config, PRICING, GCX_PER_DOLLAR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("studiomcphub")

app = Flask(
    __name__,
    static_folder="../../site/static",
    template_folder="../../site/templates",
)


# ---------------------------------------------------------------------------
# Discovery endpoints
# ---------------------------------------------------------------------------

@app.route("/.well-known/mcp.json")
def mcp_server_card():
    """MCP Server Card for auto-discovery."""
    return jsonify({
        "name": config.server_name,
        "version": config.server_version,
        "description": config.server_description,
        "url": "https://studiomcphub.com",
        "transport": "streamable-http",
        "endpoint": "https://studiomcphub.com/mcp",
        "authentication": {
            "schemes": [
                {"type": "x402", "description": "Pay per call with USDC on Base L2"},
                {"type": "bearer", "description": "API key or GCX credit token"},
                {"type": "none", "description": "Free tools (verify_provenance)"},
            ]
        },
        "tools": [
            {
                "name": name,
                "pricing": {
                    "x402_usd": p.x402_cents / 100,
                    "stripe_usd": p.stripe_cents / 100,
                    "gcx_credits": p.gcx_credits,
                }
            }
            for name, p in PRICING.items()
        ],
        "payment": {
            "x402": {
                "wallet": config.x402_wallet,
                "chain": "base",
                "token": "USDC",
            },
            "gcx": {
                "rate": f"$1 = {GCX_PER_DOLLAR} GCX",
                "purchase_url": "https://studiomcphub.com/credits",
            },
        },
        "links": {
            "documentation": "https://studiomcphub.com/docs",
            "pricing": "https://studiomcphub.com/pricing",
            "golden_codex_studio": "https://golden-codex.com",
            "github": "https://github.com/codex-curator/studiomcphub",
        },
    })


@app.route("/llms.txt")
def llms_txt():
    """LLM-readable documentation for AI discovery."""
    return (
        "# StudioMCPHub\n"
        "## Creative AI Tools for Autonomous Agents\n"
        "\n"
        "StudioMCPHub is an MCP server offering creative AI tools as paid services.\n"
        "Connect your AI agent or local assistant to generate images, upscale them,\n"
        "enrich metadata with AI analysis, embed provenance, store permanently on\n"
        "Arweave, and mint NFTs — all via the Model Context Protocol.\n"
        "\n"
        "## MCP Endpoint\n"
        "Transport: Streamable HTTP\n"
        "URL: https://studiomcphub.com/mcp\n"
        "\n"
        "## Available Tools\n"
        "\n"
        "### generate_image\n"
        "Text-to-image generation using Stable Diffusion 3.5 Large with T5-XXL encoder.\n"
        "Input: prompt (string), negative_prompt (optional), width (int), height (int)\n"
        "Output: Base64-encoded PNG image\n"
        "Price: $0.08 (x402) / $0.10 (Stripe) / 10 GCX\n"
        "\n"
        "### upscale_image\n"
        "4x super-resolution using Real-ESRGAN on NVIDIA L4 GPU.\n"
        "Input: image (base64 PNG/JPEG)\n"
        "Output: Base64-encoded upscaled PNG\n"
        "Price: $0.04 (x402) / $0.05 (Stripe) / 5 GCX\n"
        "\n"
        "### enrich_metadata\n"
        "AI-powered artwork analysis using Gemini 2.5/3.0 Pro via Nova engine.\n"
        "Generates 8-section Golden Codex JSON: title, medium, period, palette,\n"
        "composition, symbolism, emotional resonance, provenance context.\n"
        "Input: image (base64 PNG/JPEG)\n"
        "Output: Golden Codex metadata JSON\n"
        "Price: $0.03 (x402) / $0.04 (Stripe) / 4 GCX\n"
        "\n"
        "### infuse_metadata\n"
        "Embed metadata into image files using ExifTool.\n"
        "Writes XMP-gc (Golden Codex namespace), IPTC, and C2PA fields.\n"
        "Input: image (base64), metadata (Golden Codex JSON)\n"
        "Output: Base64-encoded image with embedded metadata\n"
        "Price: $0.01 (x402) / $0.02 (Stripe) / 2 GCX\n"
        "\n"
        "### register_hash\n"
        "Register perceptual hash (256-bit pHash) with LSH band indexing.\n"
        "Enables strip-proof provenance recovery even if metadata is removed.\n"
        "Input: image (base64)\n"
        "Output: hash_id, phash, registration_timestamp\n"
        "Price: $0.01 (x402) / $0.02 (Stripe) / 2 GCX\n"
        "\n"
        "### store_permanent\n"
        "Upload to Arweave L1 for permanent, immutable storage.\n"
        "Input: image (base64), metadata (optional JSON)\n"
        "Output: arweave_tx_id, arweave_url\n"
        "Price: $0.05 (x402) / $0.06 (Stripe) / 6 GCX\n"
        "\n"
        "### mint_nft\n"
        "Mint as NFT on Polygon with on-chain provenance link.\n"
        "Input: image (base64), metadata (Golden Codex JSON), collection (optional)\n"
        "Output: token_id, contract_address, tx_hash, opensea_url\n"
        "Price: $0.10 (x402) / $0.12 (Stripe) / 12 GCX\n"
        "\n"
        "### verify_provenance (FREE)\n"
        "Check an image against the Aegis hash index for provenance.\n"
        "Uses perceptual hashing — works even if metadata was stripped.\n"
        "Input: image (base64)\n"
        "Output: match_found, confidence, original_metadata (if found)\n"
        "Price: FREE\n"
        "\n"
        "### full_pipeline\n"
        "Run the complete creative pipeline: generate → upscale → enrich → infuse\n"
        "→ register → store → mint. All stages in one call.\n"
        "Input: prompt (string), options (per-stage overrides)\n"
        "Output: All stage outputs + final artifact URLs\n"
        "Price: $0.25 (x402) / $0.30 (Stripe) / 30 GCX\n"
        "\n"
        "## Payment Methods\n"
        "\n"
        "### x402 (Recommended for Agents)\n"
        "Pay per call with USDC on Base L2. No account needed.\n"
        "Server returns HTTP 402 with payment instructions.\n"
        "Agent pays on-chain, resubmits with X-PAYMENT header.\n"
        "\n"
        "### Stripe\n"
        "Traditional payment per call with API key.\n"
        "Create account at https://studiomcphub.com/signup\n"
        "\n"
        "### GCX Credits\n"
        "Pre-purchase credits: $5 = 100 GCX (~17% discount vs Stripe).\n"
        "Best value for regular users.\n"
        "\n"
        "## Human Studio\n"
        "For a full visual studio experience, visit https://golden-codex.com\n"
        "The Golden Codex Studio offers the same tools with a beautiful UI,\n"
        "batch processing, collection management, and more.\n"
    ), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/glama.json")
def glama_json():
    """Glama auto-discovery configuration."""
    return jsonify({
        "schema_version": "v1",
        "name": "studiomcphub",
        "display_name": "StudioMCPHub — Creative AI Tools",
        "description": config.server_description,
        "transport": {
            "type": "streamable-http",
            "url": "https://studiomcphub.com/mcp"
        },
        "category": "creative",
        "tags": [
            "image-generation", "upscaling", "esrgan", "stable-diffusion",
            "metadata", "provenance", "arweave", "nft", "art", "creative-ai",
            "golden-codex", "x402", "paid"
        ],
    })


# ---------------------------------------------------------------------------
# Health & status
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": config.server_name,
        "version": config.server_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/pricing")
def pricing():
    """Return pricing table for all tools."""
    return jsonify({
        "currency": "USD",
        "gcx_rate": {"dollars": 1, "gcx": GCX_PER_DOLLAR},
        "gcx_bundles": [
            {"amount_usd": 5, "gcx": 100},
            {"amount_usd": 20, "gcx": 440},   # 10% bonus
            {"amount_usd": 50, "gcx": 1200},  # 20% bonus
        ],
        "tools": {
            name: {
                "x402_usd": p.x402_cents / 100,
                "stripe_usd": p.stripe_cents / 100,
                "gcx_credits": p.gcx_credits,
            }
            for name, p in PRICING.items()
        },
    })


# ---------------------------------------------------------------------------
# Payment gate middleware
# ---------------------------------------------------------------------------

def check_payment(tool_name: str) -> tuple[str, dict] | None:
    """Check if the request includes valid payment.

    Returns (method, details) if paid, or None.
    Raises 402 response if payment required but not provided.
    """
    price = PRICING.get(tool_name)
    if not price or price.x402_cents == 0:
        return ("free", {})

    # Check x402 header
    x_payment = request.headers.get("X-PAYMENT")
    if x_payment:
        # TODO: Verify on-chain payment via x402 facilitator
        return ("x402", {"header": x_payment})

    # Check API key / GCX credit
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        # TODO: Validate token, check GCX balance, deduct credits
        return ("gcx", {"token": token})

    # Check Stripe payment intent
    stripe_pi = request.headers.get("X-Stripe-Payment-Intent")
    if stripe_pi:
        # TODO: Verify Stripe PaymentIntent is succeeded
        return ("stripe", {"payment_intent": stripe_pi})

    # No payment found — return 402
    return None


def require_payment(tool_name: str):
    """Return 402 Payment Required response with instructions."""
    price = PRICING[tool_name]
    return jsonify({
        "error": "payment_required",
        "tool": tool_name,
        "pricing": {
            "x402": {
                "amount_usd": price.x402_cents / 100,
                "wallet": config.x402_wallet,
                "chain": "base",
                "token": "USDC",
                "instructions": (
                    "Send USDC payment to wallet address, then resubmit "
                    "request with X-PAYMENT header containing the tx proof."
                ),
            },
            "stripe": {
                "amount_usd": price.stripe_cents / 100,
                "create_intent_url": "https://studiomcphub.com/api/create-payment-intent",
            },
            "gcx": {
                "credits_required": price.gcx_credits,
                "purchase_url": "https://studiomcphub.com/credits",
            },
        },
    }), 402


# ---------------------------------------------------------------------------
# MCP Tool endpoints (REST wrappers — the MCP Streamable HTTP handler
# delegates to these)
# ---------------------------------------------------------------------------

@app.route("/api/tools/<tool_name>", methods=["POST"])
def execute_tool(tool_name: str):
    """Generic tool execution endpoint with payment gating."""
    if tool_name not in PRICING:
        return jsonify({"error": f"Unknown tool: {tool_name}"}), 404

    payment = check_payment(tool_name)
    if payment is None:
        return require_payment(tool_name)

    method, details = payment
    params = request.get_json(silent=True) or {}

    logger.info(f"Executing {tool_name} | payment={method} | params={list(params.keys())}")

    # Import and dispatch to tool handler
    try:
        from src.tools import dispatch_tool
        result = dispatch_tool(tool_name, params)
        return jsonify({
            "tool": tool_name,
            "status": "success",
            "payment_method": method,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return jsonify({
            "tool": tool_name,
            "status": "error",
            "error": str(e),
        }), 500


# ---------------------------------------------------------------------------
# Support & Feedback
# ---------------------------------------------------------------------------

@app.route("/api/support/tickets", methods=["POST"])
def create_support_ticket():
    """Create a support ticket (bug, credit issue, feedback, etc.)."""
    data = request.get_json(silent=True) or {}

    required = ["type", "subject", "description"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    try:
        from src.api.support import create_ticket, TICKET_TYPES
        if data["type"] not in TICKET_TYPES:
            return jsonify({"error": f"Invalid type. Must be: {TICKET_TYPES}"}), 400

        result = create_ticket(
            ticket_type=data["type"],
            subject=data["subject"],
            description=data["description"],
            wallet_address=data.get("wallet"),
            email=data.get("email"),
            tool_name=data.get("tool"),
            tx_hash=data.get("tx_hash"),
        )
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Ticket creation failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/support/tickets/<ticket_id>", methods=["GET"])
def get_support_ticket(ticket_id: str):
    """Get a ticket by ID."""
    from src.api.support import get_ticket
    ticket = get_ticket(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify(ticket)


# ---------------------------------------------------------------------------
# Loyalty balance
# ---------------------------------------------------------------------------

@app.route("/api/loyalty/<wallet_address>", methods=["GET"])
def loyalty_balance(wallet_address: str):
    """Get loyalty credit balance for a wallet."""
    from src.payment.loyalty import get_loyalty_balance
    return jsonify(get_loyalty_balance(wallet_address))


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve landing page for humans; return MCP card for agents."""
    accept = request.headers.get("Accept", "")
    if "application/json" in accept or "text/plain" in accept:
        return mcp_server_card()
    try:
        from flask import render_template
        return render_template("index.html")
    except Exception:
        return mcp_server_card()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    logger.info(f"StudioMCPHub v{config.server_version} starting on {config.host}:{config.port}")
    app.run(host=config.host, port=config.port, debug=config.debug)


if __name__ == "__main__":
    main()
