"""StudioMCPHub tool dispatch."""

from typing import Any


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
