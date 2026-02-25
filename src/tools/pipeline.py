"""full_pipeline — Complete creative pipeline in one call.

Orchestrates: generate → upscale → enrich → infuse → register → store → mint
"""

import structlog

logger = structlog.get_logger()


def run_full_pipeline(
    prompt: str | None = None,
    image_b64: str | None = None,
    options: dict | None = None,
) -> dict:
    """Run the complete Golden Codex creative pipeline.

    Provide either a prompt (to generate) or an image (to process existing).

    Args:
        prompt: Text prompt for image generation (starts at generate stage).
        image_b64: Existing image to process (skips generate stage).
        options: Per-stage overrides, e.g.:
            {
                "generate": {"width": 1024, "height": 1024},
                "upscale": {"scale": 4},
                "enrich": {"context": "Oil painting by Monet"},
                "skip": ["mint"]  # Skip specific stages
            }

    Returns:
        dict with outputs from each stage and final artifact URLs.
    """
    if not prompt and not image_b64:
        raise ValueError("Provide either 'prompt' (for generation) or 'image' (for processing)")

    options = options or {}
    skip = set(options.get("skip", []))
    results = {"stages_completed": []}

    # Stage 1: Generate (if prompt provided)
    if prompt and "generate" not in skip:
        from .generate import generate_image
        gen_opts = options.get("generate", {})
        gen_result = generate_image(prompt=prompt, **gen_opts)
        image_b64 = gen_result["image"]
        results["generate"] = gen_result
        results["stages_completed"].append("generate")
        logger.info("pipeline: generate complete")

    # Stage 2: Upscale
    if "upscale" not in skip:
        from .upscale import upscale_image
        up_opts = options.get("upscale", {})
        up_result = upscale_image(image_b64=image_b64, **up_opts)
        image_b64 = up_result["image"]
        results["upscale"] = up_result
        results["stages_completed"].append("upscale")
        logger.info("pipeline: upscale complete")

    # Stage 3: Enrich metadata
    if "enrich" not in skip:
        from .enrich import enrich_metadata
        en_opts = options.get("enrich", {})
        en_result = enrich_metadata(image_b64=image_b64, **en_opts)
        metadata = en_result["metadata"]
        results["enrich"] = en_result
        results["stages_completed"].append("enrich")
        logger.info("pipeline: enrich complete")
    else:
        metadata = options.get("metadata", {})

    # Stage 4: Infuse metadata into image
    if "infuse" not in skip:
        from .infuse import infuse_metadata
        inf_result = infuse_metadata(image_b64=image_b64, metadata=metadata)
        image_b64 = inf_result["image"]
        results["infuse"] = inf_result
        results["stages_completed"].append("infuse")
        logger.info("pipeline: infuse complete")

    # Stage 5: Register hash
    if "register" not in skip:
        from .register import register_hash
        reg_result = register_hash(image_b64=image_b64)
        results["register"] = reg_result
        results["stages_completed"].append("register")
        logger.info("pipeline: register complete")

    # Stage 6: Permanent storage
    if "store" not in skip:
        from .store import store_permanent
        store_result = store_permanent(image_b64=image_b64, metadata=metadata)
        results["store"] = store_result
        results["stages_completed"].append("store")
        logger.info("pipeline: store complete")

    # Stage 7: Mint NFT
    if "mint" not in skip:
        from .mint import mint_nft
        mint_result = mint_nft(image_b64=image_b64, metadata=metadata)
        results["mint"] = mint_result
        results["stages_completed"].append("mint")
        logger.info("pipeline: mint complete")

    # Final output
    results["final_image"] = image_b64
    results["pipeline_complete"] = True
    logger.info("pipeline: all stages complete", stages=results["stages_completed"])

    return results
