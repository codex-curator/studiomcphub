"""infuse_metadata — Atlas metadata embedding + hash registration.

Stages base64 image to GCS, calls Atlas /infuse with GCS URL + Golden Codex
metadata. Atlas embeds XMP-gc (Golden Codex namespace), IPTC, C2PA fields,
generates a soulmark (SHA-256), and auto-registers the perceptual hash.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config
from .gcs_staging import stage_image, download_as_b64, cleanup

logger = structlog.get_logger()


def infuse_metadata(image_b64: str, metadata: dict, metadata_mode: str = "full_gcx") -> dict:
    """Embed metadata into an image via Atlas.

    Two modes:
      - full_gcx (default): Full Golden Codex XMP-gc + IPTC + C2PA + soulmark + hash registration
      - standard: XMP/IPTC fields only (title, description, keywords, copyright)

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        metadata: Metadata JSON to embed.
        metadata_mode: 'full_gcx' or 'standard'.

    Returns:
        dict with infused image (base64), soulmark, hash, fields written.
    """
    logger.info("infuse_metadata", metadata_keys=list(metadata.keys()) if isinstance(metadata, dict) else "not-dict", mode=metadata_mode)

    # Stage image to GCS (Atlas expects URLs)
    gs_url, https_url = stage_image(image_b64)

    try:
        response = httpx.post(
            f"{config.atlas_url}/infuse",
            json={
                "image_url": gs_url,
                "user_id": "mcp_agent",
                "golden_codex": metadata,
                "metadata_mode": metadata_mode,
            },
            timeout=300.0,  # Large images (4x upscaled) need time for Atlas processing
        )
        response.raise_for_status()
        data = response.json()

        atlas_status = data.get("status", "unknown")
        if atlas_status == "failed":
            error_msg = data.get("error", "unknown Atlas error")
            logger.error("infuse: Atlas returned failed status", error=error_msg)

        # Atlas returns final_url — download the infused image
        final_url = data.get("final_url") or data.get("firebase_storage_url")
        infused_b64 = None
        if final_url:
            try:
                infused_b64 = download_as_b64(final_url)
            except Exception as e:
                logger.warning("infuse: could not download final image", error=str(e))

        # Fall back to original if Atlas didn't return downloadable result
        if not infused_b64:
            infused_b64 = image_b64

        return {
            "image": infused_b64,
            "soulmark": data.get("soulmark"),
            "uuid": data.get("uuid"),
            "artifact_id": data.get("artifact_id"),
            "perceptual_hash": data.get("perceptual_hash"),
            "final_url": final_url,
            "arweave": data.get("arweave"),
            "namespace": "http://ns.goldencodex.io/schema/1.0/",
            "status": atlas_status,
        }

    finally:
        cleanup(gs_url)
