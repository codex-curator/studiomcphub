"""resize_image — Resize/crop images to target dimensions.

Supports three modes:
  - contain: Fit within bounds, preserve aspect ratio (may letterbox)
  - cover:   Crop to fill target dimensions (no letterbox)
  - stretch: Exact size, may distort aspect ratio

Uses Pillow for high-quality Lanczos resampling.
"""

import base64
import io
import logging

from PIL import Image

logger = logging.getLogger("studiomcphub.tools.resize")

MAX_INPUT_BYTES = 20 * 1024 * 1024  # 20MB input limit
MAX_DIMENSION = 8192


def resize_image(
    image_b64: str,
    width: int,
    height: int,
    mode: str = "contain",
    fmt: str = "png",
    quality: int = 90,
) -> dict:
    """Resize an image to target dimensions.

    Args:
        image_b64: Base64-encoded image (PNG/JPEG/WebP).
        width: Target width (1-8192).
        height: Target height (1-8192).
        mode: 'contain' | 'cover' | 'stretch'.
        fmt: Output format ('png', 'jpeg', 'webp').
        quality: JPEG/WebP quality (1-100).

    Returns:
        dict with image_b64, width, height, format, original_size, mode.
    """
    if not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION:
        raise ValueError(f"Dimensions must be 1-{MAX_DIMENSION}. Got {width}x{height}.")

    if mode not in ("contain", "cover", "stretch"):
        raise ValueError(f"Invalid mode '{mode}'. Use: contain, cover, stretch.")

    if fmt not in ("png", "jpeg", "webp"):
        raise ValueError(f"Invalid format '{fmt}'. Use: png, jpeg, webp.")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    img = Image.open(io.BytesIO(raw))
    orig_w, orig_h = img.size
    logger.info("resize_image: %dx%d -> %dx%d mode=%s", orig_w, orig_h, width, height, mode)

    # Convert to RGB if saving as JPEG (no alpha)
    if fmt == "jpeg" and img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = bg

    if mode == "stretch":
        result = img.resize((width, height), Image.LANCZOS)

    elif mode == "contain":
        # Fit within bounds, preserve aspect ratio
        img.thumbnail((width, height), Image.LANCZOS)
        result = img

    elif mode == "cover":
        # Scale to cover, then center-crop
        src_ratio = orig_w / orig_h
        dst_ratio = width / height

        if src_ratio > dst_ratio:
            # Source is wider — scale by height, crop width
            new_h = height
            new_w = int(orig_w * (height / orig_h))
        else:
            # Source is taller — scale by width, crop height
            new_w = width
            new_h = int(orig_h * (width / orig_w))

        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        result = img.crop((left, top, left + width, top + height))

    buf = io.BytesIO()
    save_kwargs = {}
    if fmt == "jpeg":
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    elif fmt == "webp":
        save_kwargs["quality"] = quality
    elif fmt == "png":
        save_kwargs["optimize"] = True

    pil_fmt = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}[fmt]
    result.save(buf, format=pil_fmt, **save_kwargs)
    output_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "image_b64": output_b64,
        "width": result.size[0],
        "height": result.size[1],
        "format": fmt,
        "original_size": f"{orig_w}x{orig_h}",
        "output_size_bytes": len(buf.getvalue()),
        "mode": mode,
    }
