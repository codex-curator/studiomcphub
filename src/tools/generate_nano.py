"""generate_image_nano — Google Imagen 3 fast text-to-image generation.

"Nano Banana Pro" — fast, cheap concept generation using Google's Imagen 3
via Vertex AI. Great for rapid iteration before committing to SD 3.5L renders.

Cost: 1 GCX ($0.10) vs SD 3.5L at 2 GCX ($0.20).
"""

import base64
import io
import structlog

from google.cloud import aiplatform
from vertexai.preview.vision_models import ImageGenerationModel

from ..mcp_server.config import config

logger = structlog.get_logger()

_model = None


def _get_model() -> ImageGenerationModel:
    global _model
    if _model is None:
        aiplatform.init(
            project=config.gcp_project,
            location=config.gcp_region,
        )
        _model = ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-001")
    return _model


def generate_image_nano(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    enhance_prompt: bool = True,
) -> dict:
    """Generate an image using Google Imagen 3 (fast variant).

    Args:
        prompt: Text description of the desired image.
        width: Output width (supported: 1024, 2048).
        height: Output height (supported: 1024, 2048).
        enhance_prompt: Let Imagen enhance your prompt for better results.

    Returns:
        dict with image (base64 PNG), width, height, model info.
    """
    # Imagen 3 supports specific aspect ratios, normalize to closest
    # Supported: 1:1 (1024x1024), 3:4, 4:3, 9:16, 16:9
    if width > 1536 or height > 1536:
        width = 2048 if width >= height else 1024
        height = 2048 if height >= width else 1024
    else:
        width = 1024
        height = 1024

    logger.info("generate_image_nano", prompt=prompt[:80], width=width, height=height)

    # Content safety: run the same prompt enhancer if available
    original_prompt = prompt
    enhancement_info = None

    if enhance_prompt:
        try:
            from .prompt_enhancer import enhance_prompt as _enhance
            enhancement = _enhance(prompt)
            enhancement_info = enhancement

            if enhancement.get("status") == "rejected":
                raise ValueError(
                    f"Content policy violation: {enhancement.get('rejection_reason', 'Prompt rejected')}"
                )

            prompt = enhancement.get("enhanced_prompt", prompt)
            logger.info("generate_nano.enhanced", original=original_prompt[:60], enhanced=prompt[:60])
        except ValueError:
            raise
        except Exception as e:
            logger.warning("generate_nano.enhance_failed", error=str(e))

    model = _get_model()

    response = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        add_watermark=False,  # We handle provenance via Golden Codex
    )

    if not response.images:
        raise RuntimeError("Imagen 3 returned no images")

    # Convert to base64
    image = response.images[0]
    buffer = io.BytesIO()
    image._pil_image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    result = {
        "image": image_b64,
        "width": width,
        "height": height,
        "model": "google/imagen-3.0-fast",
        "prompt": prompt,
    }

    if enhancement_info and enhancement_info.get("status") == "approved":
        result["original_prompt"] = original_prompt
        result["enhanced_prompt"] = prompt
        result["prompt_changes"] = enhancement_info.get("changes_summary", "")

    return result
