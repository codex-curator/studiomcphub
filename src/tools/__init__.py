"""StudioMCPHub tool dispatch."""

from typing import Any


# Category mapping for progressive discovery
_TOOL_CATEGORIES: dict[str, str] = {
    "generate_image": "creative",
    "upscale_image": "creative",
    "enrich_metadata": "creative",
    "infuse_metadata": "creative",
    "register_hash": "creative",
    "store_permanent": "creative",
    "mint_nft": "creative",
    "verify_provenance": "creative",
    "full_pipeline": "creative",
    "search_artworks": "dataset",
    "get_artwork": "dataset",
    "get_artwork_oracle": "dataset",
    "batch_download": "dataset",
    "compliance_manifest": "dataset",
}

# Usage examples for get_tool_schema
_TOOL_EXAMPLES: dict[str, list[dict]] = {
    "generate_image": [
        {"prompt": "A serene Japanese garden at sunset", "width": 1024, "height": 1024},
    ],
    "upscale_image": [
        {"image": "<base64-encoded-image>", "scale": 4},
    ],
    "enrich_metadata": [
        {"image": "<base64-encoded-image>", "context": "Oil on canvas, Claude Monet, 1872"},
    ],
    "infuse_metadata": [
        {"image": "<base64-encoded-image>", "metadata": {"title": "Water Lilies", "artist": "Monet"}},
    ],
    "register_hash": [
        {"image": "<base64-encoded-image>"},
    ],
    "store_permanent": [
        {"image": "<base64-encoded-image>", "metadata": {"title": "My Artwork"}},
    ],
    "mint_nft": [
        {"image": "<base64-encoded-image>", "metadata": {"title": "Genesis #1"}, "collection": "my-collection"},
    ],
    "verify_provenance": [
        {"image": "<base64-encoded-image>"},
    ],
    "full_pipeline": [
        {"prompt": "Impressionist landscape", "options": {"skip": ["mint_nft", "store_permanent"]}},
    ],
    "search_artworks": [
        {"query": "impressionist landscape", "museum": "met", "limit": 10},
    ],
    "get_artwork": [
        {"artifact_id": "met_437419"},
    ],
    "get_artwork_oracle": [
        {"artifact_id": "met_437419"},
    ],
    "batch_download": [
        {"dataset_id": "alexandria-aeternum", "quantity": 100, "offset": 0},
    ],
    "compliance_manifest": [
        {"dataset_id": "alexandria-aeternum", "regulation": "all"},
    ],
}


def dispatch_tool(tool_name: str, params: dict) -> dict[str, Any]:
    """Route a tool call to its implementation."""
    handlers = {
        "generate_image": _generate_image,
        "upscale_image": _upscale_image,
        "enrich_metadata": _enrich_metadata,
        "infuse_metadata": _infuse_metadata,
        "register_hash": _register_hash,
        "store_permanent": _store_permanent,
        "mint_nft": _mint_nft,
        "verify_provenance": _verify_provenance,
        "full_pipeline": _full_pipeline,
        # Dataset tools
        "search_artworks": _search_artworks,
        "get_artwork": _get_artwork,
        "get_artwork_oracle": _get_artwork_oracle,
        "batch_download": _batch_download,
        "compliance_manifest": _compliance_manifest,
        # Meta-tools
        "search_tools": _search_tools,
        "get_tool_schema": _get_tool_schema,
    }
    handler = handlers.get(tool_name)
    if not handler:
        raise ValueError(f"No handler for tool: {tool_name}")
    return handler(params)


def _generate_image(params: dict) -> dict:
    from .generate import generate_image
    return generate_image(
        prompt=params["prompt"],
        negative_prompt=params.get("negative_prompt", ""),
        width=params.get("width", 1024),
        height=params.get("height", 1024),
        guidance_scale=params.get("guidance_scale", 7.5),
    )


def _upscale_image(params: dict) -> dict:
    from .upscale import upscale_image
    return upscale_image(
        image_b64=params["image"],
        scale=params.get("scale", 4),
    )


def _enrich_metadata(params: dict) -> dict:
    from .enrich import enrich_metadata
    return enrich_metadata(
        image_b64=params["image"],
        context=params.get("context", ""),
    )


def _infuse_metadata(params: dict) -> dict:
    from .infuse import infuse_metadata
    return infuse_metadata(
        image_b64=params["image"],
        metadata=params["metadata"],
    )


def _register_hash(params: dict) -> dict:
    from .register import register_hash
    return register_hash(image_b64=params["image"])


def _store_permanent(params: dict) -> dict:
    from .store import store_permanent
    return store_permanent(
        image_b64=params["image"],
        metadata=params.get("metadata"),
    )


def _mint_nft(params: dict) -> dict:
    from .mint import mint_nft
    return mint_nft(
        image_b64=params["image"],
        metadata=params.get("metadata", {}),
        collection=params.get("collection"),
    )


def _verify_provenance(params: dict) -> dict:
    from .verify import verify_provenance
    return verify_provenance(image_b64=params["image"])


def _full_pipeline(params: dict) -> dict:
    from .pipeline import run_full_pipeline
    return run_full_pipeline(
        prompt=params.get("prompt"),
        image_b64=params.get("image"),
        options=params.get("options", {}),
    )


# --- Dataset tools (Alexandria Aeternum) ---

def _search_artworks(params: dict) -> dict:
    from .dataset import search_artworks
    return search_artworks(
        query=params["query"],
        museum=params.get("museum", ""),
        limit=params.get("limit", 20),
    )


def _get_artwork(params: dict) -> dict:
    from .dataset import get_artwork
    return get_artwork(artifact_id=params["artifact_id"])


def _get_artwork_oracle(params: dict) -> dict:
    from .dataset import get_artwork_oracle
    return get_artwork_oracle(artifact_id=params["artifact_id"])


def _batch_download(params: dict) -> dict:
    from .dataset import batch_download
    return batch_download(
        dataset_id=params.get("dataset_id", "alexandria-aeternum"),
        quantity=params.get("quantity", 100),
        offset=params.get("offset", 0),
    )


def _compliance_manifest(params: dict) -> dict:
    from .dataset import compliance_manifest
    return compliance_manifest(
        dataset_id=params.get("dataset_id", "alexandria-aeternum"),
        regulation=params.get("regulation", "all"),
    )


# --- Meta-tools (Progressive Discovery) ---

_META_TOOLS = {"search_tools", "get_tool_schema"}


def _search_tools(params: dict) -> dict:
    from ..mcp_server.mcp_tools import TOOL_SCHEMAS
    from ..mcp_server.config import PRICING

    query = params.get("query", "").lower()
    category = params.get("category", "all")
    max_price = params.get("max_price_usd", -1)

    results = []
    for name, schema in TOOL_SCHEMAS.items():
        # Exclude meta-tools from results (no meta-recursion)
        if name in _META_TOOLS:
            continue

        tool_cat = _TOOL_CATEGORIES.get(name, "creative")
        price = PRICING.get(name)
        price_usd = (price.x402_cents / 100) if price else 0.0
        is_free = price_usd == 0

        # Category filter
        if category == "free" and not is_free:
            continue
        if category in ("creative", "dataset") and tool_cat != category:
            continue

        # Price filter
        if max_price >= 0 and price_usd > max_price:
            continue

        # Query filter (name or description)
        if query:
            desc = schema.get("description", "").lower()
            if query not in name and query not in desc:
                continue

        # Truncate description to first sentence
        full_desc = schema.get("description", "")
        short_desc = full_desc.split(". ")[0] + "." if ". " in full_desc else full_desc

        results.append({
            "name": name,
            "description": short_desc,
            "price_usd": price_usd,
            "gcx_credits": price.gcx_credits if price else 0,
            "category": tool_cat,
            "free": is_free,
        })

    return {"tools": results, "total": len(results)}


def _get_tool_schema(params: dict) -> dict:
    from ..mcp_server.mcp_tools import TOOL_SCHEMAS
    from ..mcp_server.config import PRICING

    tool_name = params.get("tool_name", "")
    if not tool_name or tool_name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}. Use search_tools to discover available tools.")

    schema = TOOL_SCHEMAS[tool_name]
    price = PRICING.get(tool_name)
    examples = _TOOL_EXAMPLES.get(tool_name, [])

    return {
        "name": tool_name,
        "description": schema["description"],
        "inputSchema": schema["inputSchema"],
        "price_usd": (price.x402_cents / 100) if price else 0.0,
        "gcx_credits": price.gcx_credits if price else 0,
        "examples": examples,
    }
