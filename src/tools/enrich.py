"""enrich_metadata — Nova AI metadata enrichment.

Two tiers:
  - premium (default): Full 8-section Golden Codex via Nova/Gemini 2.5 Pro
  - standard: SEO-optimized title/description/keywords/alt_text via Nova-Lite
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def enrich_metadata(
    image_b64: str,
    context: str = "",
    artist_name: str = "",
    title: str = "",
    copyright_holder: str = "",
    creation_year: str = "",
    soul_whisper: dict | None = None,
) -> dict:
    """Analyze an image and generate Golden Codex metadata.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        context: Creator's brief — technical/artistic context for AI analysis.
        artist_name: Artist/creator name (embedded in final metadata).
        title: Artwork title (leave blank for AI to suggest one).
        copyright_holder: Copyright owner name.
        creation_year: 4-digit creation year.
        soul_whisper: Optional personal message dict:
            {"message": "...", "sender": "..."}

    Returns:
        dict with full Golden Codex metadata JSON.
    """
    logger.info("enrich_metadata", context=context[:80] if context else "none")

    # Detect MIME type from base64 header
    mime_type = "image/png"
    if image_b64[:20].startswith("/9j/"):
        mime_type = "image/jpeg"

    # Build Nova-compatible payload
    payload = {
        "image_data": image_b64,
        "mime_type": mime_type,
        "user_id": "mcp_agent",
        "parameters": {
            "analysis_depth": "full",
        },
    }

    # Build context string matching Nova's user_metadata_context format
    # This gets appended to the AI prompt by Nova
    context_parts = []
    if context:
        context_parts.append(f"Creator's Brief: {context}")
    if title:
        context_parts.append(f'Title: "{title}"')
    if artist_name:
        context_parts.append(f'Artist: "{artist_name}"')
    if copyright_holder:
        context_parts.append(f'Copyright Holder: "{copyright_holder}"')
    if creation_year:
        context_parts.append(f"Creation Year: {creation_year}")
    if soul_whisper and soul_whisper.get("message"):
        from datetime import datetime, timezone
        sw_date = datetime.now(timezone.utc).isoformat()
        sw_sender = soul_whisper.get("sender", artist_name or "Anonymous")
        context_parts.append('SoulWhisper ENABLED: Set "enabled": true in soulWhisper object')
        context_parts.append(f'SoulWhisper Message: "{soul_whisper["message"][:1000]}"')
        context_parts.append(f'SoulWhisper Sender: "{sw_sender}"')
        context_parts.append(f'SoulWhisper Date: "{sw_date}"')

    # Pass as context field — Nova will use it in the prompt
    if context_parts:
        payload["context"] = "\n\nUSER-PROVIDED METADATA (USE THESE VALUES EXACTLY):\n" + "\n".join(context_parts)
        payload["context"] += '\n\nIMPORTANT: If SoulWhisper fields are provided above, you MUST set "enabled": true in the soulWhisper object of your JSON output.'

    response = httpx.post(
        f"{config.nova_url}/enrich",
        json=payload,
        timeout=180.0,
    )
    response.raise_for_status()
    data = response.json()

    result = {
        "metadata": data.get("golden_codex", data),
        "model": data.get("model_used", "gemini-2.5-pro"),
        "schema_version": "1.1.0",
        "processing_time_ms": data.get("processing_time_ms"),
    }

    # Ensure soul_whisper is in metadata if provided but Nova missed it
    if soul_whisper and soul_whisper.get("message"):
        gc = result["metadata"]
        if isinstance(gc, dict) and "soulWhisper" not in gc:
            gc["soulWhisper"] = {
                "enabled": True,
                "message": soul_whisper["message"][:1000],
                "sender": soul_whisper.get("sender", artist_name or "Anonymous"),
                "date": sw_date,
            }

    return result


# Nova-Lite URL (standard tier)
_NOVA_LITE_URL = "https://nova-lite-agent-172867820131.us-west1.run.app"


def enrich_metadata_standard(
    image_b64: str,
    content_type: str = "artwork",
) -> dict:
    """Generate SEO-optimized standard metadata via Nova-Lite.

    Returns: title, description, keywords, alt_text — suitable for XMP/IPTC.
    Costs 1 GCX (half the price of premium).

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        content_type: 'artwork' or 'photo' — affects analysis style.
    """
    logger.info("enrich_metadata_standard", content_type=content_type)

    mime_type = "image/png"
    if image_b64[:20].startswith("/9j/"):
        mime_type = "image/jpeg"

    payload = {
        "image_data": image_b64,
        "mime_type": mime_type,
        "user_id": "mcp_agent",
        "parameters": {
            "analysis_depth": "standard",
            "content_type": content_type,
        },
    }

    response = httpx.post(
        f"{_NOVA_LITE_URL}/enrich",
        json=payload,
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()

    # Nova-Lite returns {title, description, keywords, alt_text} in golden_codex
    metadata = data.get("golden_codex", data)

    return {
        "tier": "standard",
        "metadata": metadata,
        "model": data.get("model_used", "gemini-2.5-flash"),
        "processing_time_ms": data.get("processing_time_ms"),
        "fields": ["title", "description", "keywords", "alt_text"],
        "note": "Standard tier: SEO-optimized XMP/IPTC fields. Use tier='premium' for full Golden Codex museum-grade analysis.",
    }
