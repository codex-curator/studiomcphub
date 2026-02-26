"""upscale_image — ESRGAN super-resolution on NVIDIA L4 GPU.

5 models available:
  realesrgan_x2plus       — 2x general (default). Fast, good for web.
  realesrgan_x4plus       — 4x general/photo. Print quality.
  realesrgan_x4plus_anime — 4x anime/illustration. Clean lines.
  realesr_general_x4v3    — 4x fast general. Lighter model.
  realesr_animevideov3    — 4x anime video frames. Fastest.

Stages base64 image to GCS, calls ESRGAN GPU service, returns upscaled base64.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config
from .gcs_staging import stage_image, download_as_b64, cleanup

logger = structlog.get_logger()

VALID_MODELS = {
    "realesrgan_x2plus",
    "realesrgan_x4plus",
    "realesrgan_x4plus_anime",
    "realesr_general_x4v3",
    "realesr_animevideov3",
}

# Scale shorthand -> default model
_SCALE_TO_MODEL = {
    2: "realesrgan_x2plus",
    4: "realesrgan_x4plus",
}

# Model -> actual scale factor
_MODEL_SCALE = {
    "realesrgan_x2plus": 2,
    "realesrgan_x4plus": 4,
    "realesrgan_x4plus_anime": 4,
    "realesr_general_x4v3": 4,
    "realesr_animevideov3": 4,
}


def upscale_image(image_b64: str, model: str | None = None, scale: int = 2) -> dict:
    """Upscale an image using Real-ESRGAN.

    Args:
        image_b64: Base64-encoded input image (PNG or JPEG).
        model: ESRGAN model name. If provided, overrides scale param.
        scale: Shorthand: 2 -> x2plus, 4 -> x4plus. Ignored if model given.

    Returns:
        dict with upscaled image (base64), dimensions, model info.
    """
    # Resolve model: explicit model > scale shorthand > default
    if model and model in VALID_MODELS:
        resolved_model = model
    elif model:
        logger.warning("upscale: invalid model %s, falling back to scale=%d", model, scale)
        resolved_model = _SCALE_TO_MODEL.get(scale, "realesrgan_x2plus")
    else:
        resolved_model = _SCALE_TO_MODEL.get(scale, "realesrgan_x2plus")

    resolved_scale = _MODEL_SCALE[resolved_model]
    original_size = len(base64.b64decode(image_b64))
    logger.info("upscale_image", input_size=original_size, model=resolved_model, scale=resolved_scale)

    # Stage image to GCS (ESRGAN only accepts GCS URLs)
    gs_url, https_url = stage_image(image_b64)

    try:
        # Call ESRGAN directly with GCS URL
        response = httpx.post(
            f"{config.esrgan_url}/upscale",
            json={
                "image_url": gs_url,
                "model": resolved_model,
            },
            timeout=300.0,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if content_type.startswith("image/"):
            # ESRGAN returned raw image bytes
            upscaled_b64 = base64.b64encode(response.content).decode()
            upscaled_size = len(response.content)
        else:
            # JSON response — may contain output URL or base64
            data = response.json()
            output_url = (data.get("output_url") or data.get("result_url")
                          or data.get("upscaled_url") or data.get("image_url"))
            if output_url:
                upscaled_b64 = download_as_b64(output_url)
                upscaled_size = len(base64.b64decode(upscaled_b64))
            elif data.get("image"):
                upscaled_b64 = data["image"]
                upscaled_size = len(base64.b64decode(upscaled_b64))
            else:
                raise ValueError(f"ESRGAN returned unexpected response: {list(data.keys())}")

        logger.info("upscale: complete", output_size=upscaled_size, model=resolved_model)

        return {
            "image": upscaled_b64,
            "scale": resolved_scale,
            "model": resolved_model,
            "original_size_bytes": original_size,
            "upscaled_size_bytes": upscaled_size,
        }

    finally:
        cleanup(gs_url)
