"""full_pipeline — Complete creative pipeline in one call.

Orchestrates: generate → upscale → enrich → infuse (includes hash registration)
Skips store and mint by default (use options to include them).
Price: 5 GCX — saves 3 GCX vs running enrich(2) + upscale(2) + infuse(1) + register(1) individually.
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
    Default: enrich + upscale + infuse (with auto hash registration).
    Use options.skip to skip stages, options.include to add store/mint.

    Args:
        prompt: Text prompt for image generation (starts at generate stage).
        image_b64: Existing image to process (skips generate stage).
        options: Per-stage overrides, e.g.:
            {
                "generate": {"width": 1024, "height": 1024},
                "upscale": {"scale": 2},  # or 4 for print-quality
                "enrich": {"context": "...", "artist_name": "...", "soul_whisper": {...}},
                "skip": ["upscale"],
                "metadata": {...}  # Pre-computed metadata (skips enrich)
            }

    Returns:
        dict with outputs from each stage and final artifact.
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
        image_b64 = gen_result.get("image_b64") or gen_result.get("image")
        results["generate"] = {k: v for k, v in gen_result.items() if k != "image" and k != "image_b64"}
        results["generate"]["has_image"] = bool(image_b64)
        results["stages_completed"].append("generate")
        logger.info("pipeline: generate complete")

    # Stage 2: Upscale
    if "upscale" not in skip:
        from .upscale import upscale_image
        up_opts = options.get("upscale", {})
        try:
            up_result = upscale_image(image_b64=image_b64, **up_opts)
            image_b64 = up_result["image"]
            results["upscale"] = {k: v for k, v in up_result.items() if k != "image"}
            results["stages_completed"].append("upscale")
            logger.info("pipeline: upscale complete", size=up_result.get("upscaled_size"))
        except Exception as e:
            logger.warning(f"pipeline: upscale failed ({e}), continuing with original")
            results["upscale"] = {"status": "skipped", "reason": str(e)}

    # Stage 3: Enrich metadata
    metadata = options.get("metadata")  # Allow pre-computed metadata
    if not metadata and "enrich" not in skip:
        from .enrich import enrich_metadata
        en_opts = options.get("enrich", {})
        en_result = enrich_metadata(image_b64=image_b64, **en_opts)
        metadata = en_result["metadata"]
        results["enrich"] = {k: v for k, v in en_result.items() if k != "metadata"}
        results["enrich"]["metadata_keys"] = list(metadata.keys()) if isinstance(metadata, dict) else []
        results["stages_completed"].append("enrich")
        logger.info("pipeline: enrich complete")

    if not metadata:
        metadata = {}

    # Stage 4: Infuse metadata + auto hash registration
    if "infuse" not in skip:
        from .infuse import infuse_metadata
        inf_result = infuse_metadata(image_b64=image_b64, metadata=metadata)
        if inf_result.get("image"):
            image_b64 = inf_result["image"]
        results["infuse"] = {k: v for k, v in inf_result.items() if k != "image"}
        results["stages_completed"].append("infuse")
        # Infuse auto-registers hash — mark it
        if inf_result.get("perceptual_hash"):
            results["stages_completed"].append("register (auto)")
        logger.info("pipeline: infuse complete", soulmark=inf_result.get("soulmark"))

    # Stage 5: Permanent storage (optional — not in default pipeline)
    if "store" not in skip and "store" in options.get("include", []):
        from .store import store_permanent
        store_result = store_permanent(image_b64=image_b64, metadata=metadata)
        results["store"] = store_result
        results["stages_completed"].append("store")
        logger.info("pipeline: store complete")

    # Stage 6: Mint NFT (optional — not in default pipeline)
    if "mint" not in skip and "mint" in options.get("include", []):
        from .mint import mint_nft
        mint_result = mint_nft(image_b64=image_b64, metadata=metadata)
        results["mint"] = mint_result
        results["stages_completed"].append("mint")
        logger.info("pipeline: mint complete")

    # Final output
    results["final_image"] = image_b64
    results["pipeline_complete"] = True
    results["golden_codex_metadata"] = metadata
    logger.info("pipeline: complete", stages=results["stages_completed"])

    return results
