"""generate_image — SD 3.5 Large + T5-XXL text-to-image generation.

Calls the Golden Codex SD 3.5 Large GPU service (Cloud Run, NVIDIA L4).
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    guidance_scale: float = 7.5,
    num_inference_steps: int = 28,
) -> dict:
    """Generate an image from a text prompt using SD 3.5 Large.

    Args:
        prompt: Text description of the desired image.
        negative_prompt: What to avoid in the image.
        width: Output width in pixels (max 2048).
        height: Output height in pixels (max 2048).
        guidance_scale: CFG scale (1.0-20.0).
        num_inference_steps: Denoising steps (1-50).

    Returns:
        dict with image (base64), width, height, seed, model info.
    """
    width = min(max(width, 512), 2048)
    height = min(max(height, 512), 2048)
    guidance_scale = min(max(guidance_scale, 1.0), 20.0)
    num_inference_steps = min(max(num_inference_steps, 1), 50)

    logger.info("generate_image", prompt=prompt[:80], width=width, height=height)

    response = httpx.post(
        f"{config.sd35_url}/generate",
        json={
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "image": data.get("image"),  # base64 PNG
        "width": width,
        "height": height,
        "model": "stabilityai/stable-diffusion-3.5-large",
        "seed": data.get("seed"),
        "prompt": prompt,
    }
