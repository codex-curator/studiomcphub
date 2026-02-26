"""GCS staging for MCP tool integrations.

MCP agents send base64 images. Backend services (Atlas, Flux, ESRGAN)
expect GCS or HTTP URLs. This module bridges the gap by staging base64
data to a temp GCS location and providing download/cleanup utilities.
"""

import base64
import time
import uuid
import structlog
from google.cloud import storage as gcs

logger = structlog.get_logger()

_STAGING_BUCKET = "the-golden-codex-1111.firebasestorage.app"
_STAGING_PREFIX = "mcp/staging"


def stage_image(image_b64: str, content_type: str = "image/png") -> tuple[str, str]:
    """Upload base64 image to GCS and return (gs_url, https_url).

    Args:
        image_b64: Base64-encoded image data.
        content_type: MIME type (image/png or image/jpeg).

    Returns:
        Tuple of (gs://url, https://url) for the staged image.
    """
    image_bytes = base64.b64decode(image_b64)
    ext = "png" if "png" in content_type else "jpg"
    ts = int(time.time())
    uid = uuid.uuid4().hex[:8]
    blob_path = f"{_STAGING_PREFIX}/{ts}_{uid}.{ext}"

    client = gcs.Client()
    bucket = client.bucket(_STAGING_BUCKET)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(image_bytes, content_type=content_type)

    gs_url = f"gs://{_STAGING_BUCKET}/{blob_path}"
    https_url = f"https://firebasestorage.googleapis.com/v0/b/{_STAGING_BUCKET}/o/{blob_path.replace('/', '%2F')}?alt=media"

    logger.info("gcs_staging: uploaded", gs_url=gs_url, size=len(image_bytes))
    return gs_url, https_url


def download_as_b64(url: str) -> str:
    """Download image from GCS or HTTP URL and return as base64.

    Args:
        url: GCS (gs://) or HTTP(S) URL.

    Returns:
        Base64-encoded image data.
    """
    import re

    if url.startswith("gs://"):
        match = re.match(r"gs://([^/]+)/(.+)", url)
        if not match:
            raise ValueError(f"Invalid GCS URL: {url}")
        bucket_name, blob_path = match.groups()
        client = gcs.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        image_bytes = blob.download_as_bytes()
    elif url.startswith("http"):
        import httpx
        resp = httpx.get(url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        image_bytes = resp.content
    else:
        raise ValueError(f"Unsupported URL scheme: {url}")

    logger.info("gcs_staging: downloaded", url=url[:80], size=len(image_bytes))
    return base64.b64encode(image_bytes).decode()


def cleanup(gs_url: str):
    """Delete a staged file (best-effort)."""
    import re
    try:
        match = re.match(r"gs://([^/]+)/(.+)", gs_url)
        if match:
            bucket_name, blob_path = match.groups()
            client = gcs.Client()
            client.bucket(bucket_name).blob(blob_path).delete()
            logger.info("gcs_staging: cleaned up", path=blob_path)
    except Exception as e:
        logger.warning("gcs_staging: cleanup failed", error=str(e))
