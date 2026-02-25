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
import uuid
import os
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory, Response
from mcp.types import ListToolsRequest, CallToolRequest, CallToolRequestParams

from .config import config, PRICING, GCX_PER_DOLLAR
from .mcp_tools import create_mcp_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("studiomcphub")

# Resolve path to the site/ directory (for landing page serving)
_SITE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "site")

app = Flask(
    __name__,
    static_folder="../../site/static",
    template_folder="../../site/templates",
)

# MCP session store: session_id -> (server, transport)
_mcp_sessions: dict[str, tuple] = {}


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


@app.route("/.well-known/agent.json")
def a2a_agent_card():
    """A2A Agent Card for agent-to-agent discovery."""
    return send_from_directory(
        os.path.join(_SITE_DIR, ".well-known"), "agent.json",
        mimetype="application/json",
    )


@app.route("/llms.txt")
def llms_txt():
    """LLM-readable documentation for AI discovery."""
    return send_from_directory(_SITE_DIR, "llms.txt", mimetype="text/plain")


@app.route("/glama.json")
def glama_json():
    """Glama auto-discovery configuration."""
    return jsonify({
        "schema_version": "v1",
        "name": "studiomcphub",
        "display_name": "StudioMCPHub — Creative AI Tools + Art Datasets",
        "description": config.server_description,
        "transport": {
            "type": "streamable-http",
            "url": "https://studiomcphub.com/mcp"
        },
        "category": "creative",
        "tags": [
            "image-generation", "upscaling", "esrgan", "stable-diffusion",
            "metadata", "provenance", "arweave", "nft", "art", "creative-ai",
            "golden-codex", "x402", "paid", "dataset", "museum-art",
            "alexandria-aeternum", "art-history", "compliance"
        ],
    })


# ---------------------------------------------------------------------------
# MCP Streamable HTTP transport
# ---------------------------------------------------------------------------

@app.route("/mcp", methods=["POST", "GET", "DELETE"])
def mcp_endpoint():
    """MCP Streamable HTTP endpoint.

    POST: Send MCP JSON-RPC messages (initialize, tools/list, tools/call).
    GET:  SSE stream for server-initiated notifications (long-poll).
    DELETE: Terminate an MCP session.
    """
    import asyncio

    session_id = request.headers.get("Mcp-Session-Id")

    if request.method == "POST":
        body = request.get_data(as_text=True)
        if not body:
            return jsonify({"error": "Empty request body"}), 400

        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON"}), 400

        # Initialize: create new session
        if msg.get("method") == "initialize":
            sid = str(uuid.uuid4())
            server = create_mcp_server(check_payment)
            _mcp_sessions[sid] = server

            # Return MCP initialize response with session ID
            return Response(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg.get("id"),
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {
                            "tools": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": config.server_name,
                            "version": config.server_version,
                        },
                    },
                }),
                status=200,
                content_type="application/json",
                headers={"Mcp-Session-Id": sid},
            )

        # All other methods require existing session
        if not session_id or session_id not in _mcp_sessions:
            return jsonify({"error": "Invalid or missing Mcp-Session-Id"}), 400

        server = _mcp_sessions[session_id]

        # Handle notifications (no id field) — just acknowledge
        if "id" not in msg:
            return Response("", status=202)

        # tools/list
        if msg.get("method") == "tools/list":
            handler = server.request_handlers.get(ListToolsRequest)
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(handler(ListToolsRequest(
                    method="tools/list",
                    params=None,
                )))
            finally:
                loop.close()
            return Response(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg.get("id"),
                    "result": result.model_dump(exclude_none=True) if hasattr(result, "model_dump") else result,
                }),
                status=200,
                content_type="application/json",
                headers={"Mcp-Session-Id": session_id},
            )

        # tools/call
        if msg.get("method") == "tools/call":
            call_params = msg.get("params", {})
            tool_name = call_params.get("name", "")
            arguments = call_params.get("arguments", {})

            # Payment gate: check before dispatching
            price = PRICING.get(tool_name)
            if price and price.gcx_credits > 0:
                payment = check_payment(tool_name)
                if payment is None:
                    return require_payment(tool_name)

            handler = server.request_handlers.get(CallToolRequest)
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(handler(CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(name=tool_name, arguments=arguments),
                )))
            finally:
                loop.close()

            return Response(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg.get("id"),
                    "result": result.model_dump(exclude_none=True) if hasattr(result, "model_dump") else result,
                }),
                status=200,
                content_type="application/json",
                headers={"Mcp-Session-Id": session_id},
            )

        return jsonify({
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "error": {"code": -32601, "message": f"Method not found: {msg.get('method')}"},
        }), 200

    elif request.method == "GET":
        # SSE endpoint for server-initiated messages (not implemented yet)
        if not session_id or session_id not in _mcp_sessions:
            return jsonify({"error": "Invalid session"}), 400
        return Response("", status=200, content_type="text/event-stream")

    elif request.method == "DELETE":
        # Terminate session
        if session_id and session_id in _mcp_sessions:
            del _mcp_sessions[session_id]
        return Response("", status=200)

    return jsonify({"error": "Method not allowed"}), 405


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
        from ..payment.x402 import verify_payment, extract_wallet
        from ..payment.agent_tiers import apply_discount
        base_usd = price.x402_cents / 100
        wallet = extract_wallet(x_payment)
        if wallet:
            discounted_usd, tier_info = apply_discount(wallet, base_usd)
        else:
            discounted_usd, tier_info = base_usd, {"label": "Standard", "discount_pct": 0}
        verified_usd = None
        if verify_payment(x_payment, discounted_usd):
            verified_usd = discounted_usd
        elif discounted_usd != base_usd and verify_payment(x_payment, base_usd):
            verified_usd = base_usd

        if verified_usd is not None:
            # Post-payment hooks (fire-and-forget)
            if wallet:
                try:
                    from ..payment.agent_tiers import record_spend
                    record_spend(wallet, verified_usd, tool_name)
                except Exception as e:
                    logger.warning(f"record_spend failed: {e}")
                try:
                    from ..payment.gcx_credits import ensure_account
                    ensure_account(wallet)
                except Exception as e:
                    logger.warning(f"ensure_account failed: {e}")
                try:
                    from ..payment.loyalty import earn_loyalty
                    earn_loyalty(wallet, price.gcx_credits, tool_name)
                except Exception as e:
                    logger.warning(f"earn_loyalty failed: {e}")
            return ("x402", {"header": x_payment, "wallet": wallet, "tier": tier_info, "amount_usd": verified_usd})

        logger.warning(f"x402 payment verification failed for {tool_name}")
        return None

    # Check API key / GCX credit (Bearer token = user_id for GCX)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        from ..payment.gcx_credits import deduct_credits
        if deduct_credits(user_id=token, amount=price.gcx_credits, tool_name=tool_name):
            # Post-payment hook: loyalty credit-back (fire-and-forget)
            try:
                from ..payment.loyalty import earn_loyalty
                earn_loyalty(token, price.gcx_credits, tool_name)
            except Exception as e:
                logger.warning(f"earn_loyalty failed: {e}")
            return ("gcx", {"token": token, "gcx_deducted": price.gcx_credits})
        logger.warning(f"GCX deduction failed for {tool_name} (user={token})")
        return None

    # Check Stripe payment intent
    stripe_pi = request.headers.get("X-Stripe-Payment-Intent")
    if stripe_pi:
        from ..payment.stripe_pay import verify_payment_intent
        if verify_payment_intent(stripe_pi):
            return ("stripe", {"payment_intent": stripe_pi})
        logger.warning(f"Stripe PI verification failed for {tool_name}")
        return None

    # No payment found — return 402
    return None


def require_payment(tool_name: str):
    """Return 402 Payment Required response with instructions."""
    from .config import AGENT_VOLUME_TIERS
    price = PRICING[tool_name]
    base_usd = price.x402_cents / 100
    return jsonify({
        "error": "payment_required",
        "tool": tool_name,
        "pricing": {
            "x402": {
                "amount_usd": base_usd,
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
        "volume_discounts": {
            "check_url": "https://studiomcphub.com/api/agent/tier/{wallet_address}",
            "tiers": [
                {"label": t["label"], "min_spend_usd": t["min_spend_usd"], "discount_pct": t["discount_pct"]}
                for t in AGENT_VOLUME_TIERS
            ],
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
        from ..tools import dispatch_tool
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
        from ..api.support import create_ticket, TICKET_TYPES
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
    from ..api.support import get_ticket
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
    from ..payment.loyalty import get_loyalty_balance
    return jsonify(get_loyalty_balance(wallet_address))


@app.route("/api/agent/tier/<wallet_address>", methods=["GET"])
def agent_tier(wallet_address: str):
    """Get volume discount tier for a wallet."""
    from ..payment.agent_tiers import get_tier
    return jsonify(get_tier(wallet_address))


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
        return send_from_directory(_SITE_DIR, "index.html")
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
