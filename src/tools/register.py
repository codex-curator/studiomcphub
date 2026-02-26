"""register_hash — Aegis perceptual hash registration.

Stages base64 image to GCS, calls Atlas /register-hash endpoint.
Registers a 256-bit perceptual hash with LSH 16x4 band indexing
for O(candidates) provenance lookup at 100K+ scale.

Note: If you're running the full pipeline, infuse_metadata already
auto-registers the hash — no need to call this separately.
"""

import base64
import httpx
import structlog
from datetime import datetime, timezone

from ..mcp_server.config import config
from .gcs_staging import stage_image, cleanup

logger = structlog.get_logger()


def register_hash(image_b64: str) -> dict:
    """Register an image's perceptual hash in the Aegis index.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).

    Returns:
        dict with hash_id, phash (hex), lsh_bands, registration timestamp.
    """
    logger.info("register_hash")

    # Stage image to GCS (Atlas expects URLs)
    gs_url, https_url = stage_image(image_b64)

    try:
        response = httpx.post(
            f"{config.atlas_url}/register-hash",
            json={
                "image_url": gs_url,
                "gcx_id": f"MCP-{int(datetime.now(timezone.utc).timestamp())}",
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        return {
            "success": data.get("success", False),
            "hash_id": data.get("gcx_id"),
            "phash": data.get("computed_hash"),
            "index_stats": data.get("index_stats"),
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "index_type": "LSH_16x4",
        }

    finally:
        cleanup(gs_url)
