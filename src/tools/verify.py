"""verify_provenance — Aegis strip-proof provenance verification (FREE).

Stages base64 image to GCS, calls Atlas /lookup-image endpoint.
Works even if all metadata has been stripped from the image.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config
from .gcs_staging import stage_image, cleanup

logger = structlog.get_logger()


def verify_provenance(image_b64: str) -> dict:
    """Verify an image's provenance using perceptual hash lookup.

    This tool is FREE — no payment required. It encourages ecosystem
    adoption by letting anyone verify provenance.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).

    Returns:
        dict with match_found, confidence, original_metadata (if found).
    """
    logger.info("verify_provenance")

    # Stage image to GCS (Atlas expects URLs)
    gs_url, https_url = stage_image(image_b64)

    try:
        response = httpx.post(
            f"{config.atlas_url}/lookup-image",
            json={"image_url": gs_url},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        best = data.get("best_match") or {}

        return {
            "match_found": data.get("match_found", False),
            "confidence": best.get("similarity", 0.0),
            "computed_hash": data.get("computed_hash"),
            "best_match": {
                "gcx_id": best.get("gcx_id"),
                "title": best.get("title"),
                "artist": best.get("artist"),
                "similarity": best.get("similarity"),
                "provenance_uri": best.get("provenance_uri"),
            } if best else None,
            "total_matches": len(data.get("matches", [])),
            "index_stats": data.get("index_stats"),
        }

    finally:
        cleanup(gs_url)
