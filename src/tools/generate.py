"""generate_image — SD 3.5 Large + T5-XXL text-to-image generation.

Calls the Golden Codex SD 3.5 Large GPU service (Cloud Run, NVIDIA L4).
Includes LLM prompt enhancement and content safety filtering via Gemini.
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
    enhance_prompt: bool = True,
) -> dict:
    """Generate an image from a text prompt using SD 3.5 Large.

    The prompt is first enhanced by Gemini for optimal SD 3.5 output
    and checked for content policy violations.

    Args:
        prompt: Text description of the desired image.
        negative_prompt: What to avoid in the image.
        width: Output width in pixels (max 2048).
        height: Output height in pixels (max 2048).
        guidance_scale: CFG scale (1.0-20.0).
        num_inference_steps: Denoising steps (1-50).
        enhance_prompt: Whether to run LLM prompt enhancement (default True).

    Returns:
        dict with image (base64), width, height, seed, model info,
        plus original_prompt and enhanced_prompt when enhancement is used.
    """
    width = min(max(width, 512), 2048)
    height = min(max(height, 512), 2048)
    guidance_scale = min(max(guidance_scale, 1.0), 20.0)
    num_inference_steps = min(max(num_inference_steps, 1), 50)

    original_prompt = prompt
    enhancement_info = None

    # Step 1: Enhance prompt via Gemini (content safety + quality improvement)
    if enhance_prompt:
        try:
            from .prompt_enhancer import enhance_prompt as _enhance
            enhancement = _enhance(prompt)
            enhancement_info = enhancement

            if enhancement.get("status") == "rejected":
                raise ValueError(
                    f"Content policy violation: {enhancement.get('rejection_reason', 'Prompt rejected')}"
                )

            # Use enhanced prompt and negative
            prompt = enhancement.get("enhanced_prompt", prompt)
            if not negative_prompt and enhancement.get("negative_prompt"):
                negative_prompt = enhancement["negative_prompt"]

            logger.info("generate_image.enhanced", original=original_prompt[:60], enhanced=prompt[:60])
        except ValueError:
            raise  # Re-raise content policy rejections
        except Exception as e:
            # Enhancement failure is non-fatal — use original prompt
            logger.warning("generate_image.enhance_failed", error=str(e))

    logger.info("generate_image", prompt=prompt[:80], width=width, height=height)

    # Step 2: Call SD 3.5 Large
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

    result = {
        "image": data.get("image"),  # base64 PNG
        "width": width,
        "height": height,
        "model": "stabilityai/stable-diffusion-3.5-large",
        "seed": data.get("seed"),
        "prompt": prompt,
    }

    # Include enhancement details so the caller sees what changed
    if enhancement_info and enhancement_info.get("status") == "approved":
        result["original_prompt"] = original_prompt
        result["enhanced_prompt"] = prompt
        result["prompt_changes"] = enhancement_info.get("changes_summary", "")

    return result
