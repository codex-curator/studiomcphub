"""upscale_image — ESRGAN x4 super-resolution.

Calls the Golden Codex ESRGAN GPU service (Cloud Run, NVIDIA L4).
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def upscale_image(image_b64: str, scale: int = 4) -> dict:
    """Upscale an image using Real-ESRGAN x4plus.

    Args:
        image_b64: Base64-encoded input image (PNG or JPEG).
        scale: Upscale factor (2 or 4). Default 4.

    Returns:
        dict with upscaled image (base64), dimensions, model info.
    """
    scale = 4 if scale not in (2, 4) else scale

    image_bytes = base64.b64decode(image_b64)
    logger.info("upscale_image", input_size=len(image_bytes), scale=scale)

    response = httpx.post(
        f"{config.esrgan_url}/upscale",
        json={"image": image_b64, "scale": scale},
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "image": data.get("image"),  # base64 PNG
        "scale": scale,
        "model": "RealESRGAN_x4plus",
        "original_size": len(image_bytes),
    }
