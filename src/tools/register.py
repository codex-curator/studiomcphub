"""register_hash — Aegis perceptual hash registration.

Registers a 256-bit perceptual hash with LSH 16x4 band indexing
for O(candidates) provenance lookup at 100K+ scale.
"""

import base64
import httpx
import structlog
from datetime import datetime, timezone

from ..mcp_server.config import config

logger = structlog.get_logger()


def register_hash(image_b64: str) -> dict:
    """Register an image's perceptual hash in the Aegis index.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).

    Returns:
        dict with hash_id, phash (hex), lsh_bands, registration timestamp.
    """
    logger.info("register_hash")

    response = httpx.post(
        f"{config.atlas_url}/register-hash",
        json={"image": image_b64},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "hash_id": data.get("hash_id"),
        "phash": data.get("phash"),
        "lsh_bands": data.get("lsh_bands"),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "index_type": "LSH_16x4",
    }
