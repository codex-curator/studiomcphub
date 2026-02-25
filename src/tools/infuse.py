"""infuse_metadata — Atlas ExifTool metadata embedding.

Embeds Golden Codex metadata into image files using ExifTool.
Writes to XMP-gc (Golden Codex namespace), IPTC, and C2PA fields.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def infuse_metadata(image_b64: str, metadata: dict) -> dict:
    """Embed metadata into an image file using ExifTool.

    The metadata is gzip-compressed and base64-encoded into the
    XMP-gc:CodexPayload field (Golden Codex namespace).

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        metadata: Golden Codex metadata JSON to embed.

    Returns:
        dict with infused image (base64), embedded fields list.
    """
    logger.info("infuse_metadata", metadata_keys=list(metadata.keys()))

    response = httpx.post(
        f"{config.atlas_url}/infuse",
        json={
            "image": image_b64,
            "metadata": metadata,
            "namespace": "gc",
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "image": data.get("image"),  # base64 with embedded metadata
        "fields_written": data.get("fields_written", []),
        "namespace": "http://ns.goldencodex.io/schema/1.0/",
    }
