"""enrich_metadata — Nova AI metadata enrichment.

Uses Gemini 2.5/3.0 Pro via the Nova engine to generate a structured
Golden Codex metadata JSON with 8 analytical sections.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def enrich_metadata(image_b64: str, context: str = "") -> dict:
    """Analyze an image and generate Golden Codex metadata.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        context: Optional context about the artwork (artist, title, etc.).

    Returns:
        dict with full Golden Codex metadata JSON including:
        - title, artist attribution, medium, period
        - palette analysis, composition breakdown
        - symbolism and iconography
        - emotional resonance mapping
        - provenance context
    """
    logger.info("enrich_metadata", context=context[:80] if context else "none")

    response = httpx.post(
        f"{config.nova_url}/enrich",
        json={
            "image": image_b64,
            "context": context,
            "output_format": "golden_codex_v1.1",
        },
        timeout=180.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "metadata": data.get("golden_codex", data),
        "model": "gemini-2.5-pro",
        "schema_version": "1.1.0",
    }
