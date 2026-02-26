"""prompt_enhancer — LLM-powered prompt improvement + content safety for SD 3.5.

Takes a raw user prompt, enhances it for optimal SD 3.5 Large output,
checks for content policy violations, and generates an optimized negative prompt.

Uses Vertex AI Gemini 2.5 Flash for speed (typically <2s).
"""

import structlog
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part

from ..mcp_server.config import config

logger = structlog.get_logger()

# Lazy-init to avoid import-time GCP calls
_model = None


def _get_model() -> GenerativeModel:
    global _model
    if _model is None:
        aiplatform.init(
            project=config.gcp_project,
            location=config.gcp_region,
        )
        _model = GenerativeModel("gemini-2.5-flash")
    return _model


# Content categories that should be blocked
BLOCKED_CATEGORIES = [
    "child exploitation", "minors in sexual contexts", "csam",
    "weapons of mass destruction", "bioweapons", "chemical weapons",
    "real person deepfake", "non-consensual intimate imagery",
    "extreme graphic violence", "hate symbols targeting protected groups",
]

SYSTEM_PROMPT = """You are a professional prompt engineer for Stable Diffusion 3.5 Large with T5-XXL text encoder.

## YOUR TASK
Take the user's image generation prompt, enhance it for optimal SD 3.5 Large output, and check for content policy violations.

## ENHANCEMENT RULES
1. Preserve the user's core intent and subject matter
2. Add structure: subject → style → lighting → details → quality terms
3. Use natural language (T5-XXL understands full sentences, not just tags)
4. Add quality boosters: "masterpiece, highly detailed, professional"
5. Add appropriate lighting if not specified
6. Add texture keywords for ESRGAN-friendly output (skin pores, fabric weave, etc.)
7. Keep enhanced prompt under 200 tokens
8. Do NOT add artist names unless the user mentioned a style

## CONTENT POLICY
REJECT prompts that request:
- Child exploitation or sexualized minors in any form
- Weapons of mass destruction instructions
- Real-person deepfakes or non-consensual intimate imagery
- Extreme graphic violence (gore, torture)
- Hate symbols targeting protected groups

Normal artistic content (nudity in fine art context, fantasy violence, dark themes) is ALLOWED.

## OUTPUT FORMAT (JSON only, no markdown)
{
  "status": "approved" or "rejected",
  "enhanced_prompt": "the improved prompt (only if approved)",
  "negative_prompt": "quality exclusions (only if approved)",
  "rejection_reason": "why it was rejected (only if rejected)",
  "changes_summary": "brief note on what was improved"
}"""


def enhance_prompt(raw_prompt: str) -> dict:
    """Enhance a prompt for SD 3.5 Large generation.

    Args:
        raw_prompt: The user's original text prompt.

    Returns:
        dict with status, enhanced_prompt, negative_prompt, and changes_summary.
        If rejected: status="rejected" with rejection_reason.
    """
    import json

    model = _get_model()

    logger.info("prompt_enhancer.start", raw_prompt=raw_prompt[:80])

    response = model.generate_content(
        [
            Part.from_text(SYSTEM_PROMPT),
            Part.from_text(f"Enhance this prompt:\n\n{raw_prompt}"),
        ],
        generation_config={
            "temperature": 0.3,
            "max_output_tokens": 512,
            "response_mime_type": "application/json",
        },
    )

    try:
        result = json.loads(response.text)
    except (json.JSONDecodeError, ValueError):
        # Fallback: use raw prompt if Gemini returns non-JSON
        logger.warning("prompt_enhancer.parse_failed", raw=response.text[:200])
        result = {
            "status": "approved",
            "enhanced_prompt": raw_prompt,
            "negative_prompt": "(worst quality, low quality:1.4), blurry, text, watermark, signature",
            "changes_summary": "Enhancement unavailable, using original prompt",
        }

    logger.info(
        "prompt_enhancer.done",
        status=result.get("status"),
        changes=result.get("changes_summary", "")[:80],
    )

    return result
