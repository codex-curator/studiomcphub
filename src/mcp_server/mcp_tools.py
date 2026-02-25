"""MCP tool registrations for StudioMCPHub Streamable HTTP transport.

Registers all 14 tools as proper MCP tools with payment gating.
Each tool checks payment, dispatches to the existing tool implementation,
and returns MCP-formatted results.
"""

import json
import logging
from datetime import datetime, timezone

from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)

from .config import PRICING

logger = logging.getLogger("studiomcphub.mcp")

# Tool input schemas for MCP discovery
TOOL_SCHEMAS = {
    "generate_image": {
        "description": "Text-to-image generation using SD 3.5 Large + T5-XXL on NVIDIA L4 GPU.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt for image generation"},
                "negative_prompt": {"type": "string", "description": "Negative prompt", "default": ""},
                "width": {"type": "integer", "description": "Image width (512-2048)", "default": 1024},
                "height": {"type": "integer", "description": "Image height (512-2048)", "default": 1024},
                "guidance_scale": {"type": "number", "description": "CFG scale (1.0-20.0)", "default": 7.5},
            },
            "required": ["prompt"],
        },
    },
    "upscale_image": {
        "description": "4x super-resolution using Real-ESRGAN on NVIDIA L4 GPU.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
                "scale": {"type": "integer", "description": "Upscale factor (2 or 4)", "default": 4},
            },
            "required": ["image"],
        },
    },
    "enrich_metadata": {
        "description": "AI-powered artwork analysis via Gemini 2.5/3.0 Pro. Returns 8-section Golden Codex JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
                "context": {"type": "string", "description": "Optional context (artist, title, etc.)", "default": ""},
            },
            "required": ["image"],
        },
    },
    "infuse_metadata": {
        "description": "Embed Golden Codex metadata into image via ExifTool (XMP-gc, IPTC, C2PA).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
                "metadata": {"type": "object", "description": "Golden Codex metadata JSON to embed"},
            },
            "required": ["image", "metadata"],
        },
    },
    "register_hash": {
        "description": "Register 256-bit perceptual hash with LSH band indexing for strip-proof provenance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
            },
            "required": ["image"],
        },
    },
    "store_permanent": {
        "description": "Upload to Arweave L1 for permanent, immutable storage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
                "metadata": {"type": "object", "description": "Optional metadata JSON to store alongside"},
            },
            "required": ["image"],
        },
    },
    "mint_nft": {
        "description": "Mint as NFT on Polygon with on-chain provenance link.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
                "metadata": {"type": "object", "description": "Golden Codex metadata JSON"},
                "collection": {"type": "string", "description": "Optional collection name or ID"},
            },
            "required": ["image"],
        },
    },
    "verify_provenance": {
        "description": "Strip-proof provenance verification via Aegis hash index. FREE - no payment required.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded PNG/JPEG image"},
            },
            "required": ["image"],
        },
    },
    "full_pipeline": {
        "description": "Complete creative pipeline: generate/upscale/enrich/infuse/register/store/mint in one call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt (provide this OR image)"},
                "image": {"type": "string", "description": "Base64 image (provide this OR prompt)"},
                "options": {"type": "object", "description": "Per-stage overrides and skip list"},
            },
        },
    },
    # --- Alexandria Aeternum Dataset Tools ---
    "search_artworks": {
        "description": "Search 53K+ museum artworks from Alexandria Aeternum (MET, Chicago, NGA, Rijksmuseum, Smithsonian, Cleveland, Paris). FREE.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'impressionist landscape', 'Monet', 'Dutch Golden Age')"},
                "museum": {"type": "string", "description": "Filter by museum (met, chicago, nga, rijks, smithsonian, cleveland, paris)", "default": ""},
                "limit": {"type": "integer", "description": "Max results (1-100)", "default": 20},
            },
            "required": ["query"],
        },
    },
    "get_artwork": {
        "description": "Get Human_Standard metadata (500-1200 tokens) + signed image URL for a museum artwork.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID from search results (e.g. 'met_437419')"},
            },
            "required": ["artifact_id"],
        },
    },
    "get_artwork_oracle": {
        "description": "Get Hybrid_Premium 111-field NEST analysis (2K-6K tokens) + image. Deep AI visual analysis with color palette, composition, symbolism, emotional mapping.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID from search results (e.g. 'met_437419')"},
            },
            "required": ["artifact_id"],
        },
    },
    "batch_download": {
        "description": "Bulk download metadata + images from Alexandria Aeternum (min 100 artworks).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "Dataset ID", "default": "alexandria-aeternum"},
                "quantity": {"type": "integer", "description": "Number of artworks (min 100)", "default": 100},
                "offset": {"type": "integer", "description": "Start offset for pagination", "default": 0},
            },
        },
    },
    "compliance_manifest": {
        "description": "Get AB 2013 (California) + EU AI Act Article 53 compliance manifests for dataset usage. FREE.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string", "description": "Dataset ID", "default": "alexandria-aeternum"},
                "regulation": {"type": "string", "description": "Filter: ab2013, eu_ai_act, or all", "default": "all"},
            },
        },
    },
    # --- Meta-tools (Progressive Discovery) ---
    "search_tools": {
        "description": "Discover available tools by category or price without loading all schemas. Start here to save tokens.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query to filter tools by name or description", "default": ""},
                "category": {
                    "type": "string",
                    "description": "Filter by category",
                    "enum": ["creative", "dataset", "free", "all"],
                    "default": "all",
                },
                "max_price_usd": {"type": "number", "description": "Max price per call in USD (0 = free only)", "default": -1},
            },
        },
    },
    "get_tool_schema": {
        "description": "Get the full JSON Schema and usage examples for a specific tool. Use after search_tools to load only what you need.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string", "description": "Tool name from search_tools results (e.g. 'generate_image')"},
            },
            "required": ["tool_name"],
        },
    },
}


def create_mcp_server(check_payment_fn) -> Server:
    """Create and configure an MCP Server with all tools registered.

    Args:
        check_payment_fn: Callable(tool_name, headers) -> (method, details) | None
            Payment verification function. Returns None if payment required.
    """
    server = Server("StudioMCPHub")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        for name, schema in TOOL_SCHEMAS.items():
            price = PRICING.get(name)
            price_note = f" (${price.x402_cents / 100:.2f} / {price.gcx_credits} GCX)" if price and price.gcx_credits > 0 else " (FREE)"
            tools.append(Tool(
                name=name,
                description=schema["description"] + price_note,
                inputSchema=schema["inputSchema"],
            ))
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name not in TOOL_SCHEMAS:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        # Payment gating is handled at the HTTP layer (check_payment in server.py).
        # By the time we reach here, payment has already been verified by the
        # Flask /mcp handler. We just dispatch and return.
        try:
            from ..tools import dispatch_tool
            result = dispatch_tool(name, arguments)
            return [TextContent(type="text", text=json.dumps({
                "tool": name,
                "status": "success",
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))]
        except Exception as e:
            logger.error(f"MCP tool {name} failed: {e}")
            return [TextContent(type="text", text=json.dumps({
                "tool": name,
                "status": "error",
                "error": str(e),
            }))]

    return server
