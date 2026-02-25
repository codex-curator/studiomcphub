"""verify_provenance — Aegis strip-proof provenance verification (FREE).

Checks an image against the Aegis perceptual hash index.
Works even if all metadata has been stripped from the image.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def verify_provenance(image_b64: str) -> dict:
    """Verify an image's provenance using perceptual hash lookup.

    This tool is FREE — no payment required. It encourages ecosystem
    adoption by letting anyone verify provenance.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).

    Returns:
        dict with match_found, confidence, original_metadata (if found),
        registration_date, arweave_url (if stored).
    """
    logger.info("verify_provenance")

    response = httpx.post(
        f"{config.atlas_url}/verify",
        json={"image": image_b64},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "match_found": data.get("match_found", False),
        "confidence": data.get("confidence", 0.0),
        "phash_distance": data.get("distance"),
        "original_metadata": data.get("metadata"),
        "registration_date": data.get("registered_at"),
        "arweave_url": data.get("arweave_url"),
        "golden_codex_url": data.get("codex_url"),
    }
