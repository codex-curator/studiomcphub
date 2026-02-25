"""store_permanent — Archivus Arweave L1 permanent storage.

Uploads image and metadata to Arweave for permanent, immutable storage.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def store_permanent(image_b64: str, metadata: dict | None = None) -> dict:
    """Store an image permanently on Arweave L1.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        metadata: Optional metadata JSON to store alongside the image.

    Returns:
        dict with arweave_tx_id, arweave_url, size_bytes, cost_ar.
    """
    logger.info("store_permanent", has_metadata=metadata is not None)

    response = httpx.post(
        f"{config.archivus_url}/store",
        json={
            "image": image_b64,
            "metadata": metadata,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "arweave_tx_id": data.get("tx_id"),
        "arweave_url": f"https://arweave.net/{data.get('tx_id')}",
        "size_bytes": data.get("size_bytes"),
        "cost_ar": data.get("cost_ar"),
        "permanent": True,
    }
