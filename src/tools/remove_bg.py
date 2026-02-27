"""remove_background -- Remove image background using rembg (U2-Net).

Lazy-imports rembg to avoid loading the ~200MB model at startup.
"""

import base64
import io
import logging

from PIL import Image

logger = logging.getLogger("studiomcphub.tools.remove_bg")

MAX_INPUT_BYTES = 20 * 1024 * 1024


def remove_background(
    image_b64: str,
    output_format: str = "png",
) -> dict:
    """Remove the background from an image.

    Args:
        image_b64: Base64-encoded image (PNG/JPEG/WebP).
        output_format: Output format ('png' or 'webp'). Default 'png'.

    Returns:
        dict with image_b64 (RGBA), width, height, format, output_size_bytes.
    """
    if output_format not in ("png", "webp"):
        raise ValueError(f"Invalid output_format '{output_format}'. Use: png, webp.")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    logger.info("remove_background: input %d bytes, output_format=%s", len(raw), output_format)

    # Lazy import to avoid loading U2-Net model at startup
    from rembg import remove

    result_bytes = remove(raw)
    img = Image.open(io.BytesIO(result_bytes))

    # Ensure RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    buf = io.BytesIO()
    pil_fmt = "PNG" if output_format == "png" else "WEBP"
    save_kwargs = {"optimize": True} if output_format == "png" else {"quality": 90}
    img.save(buf, format=pil_fmt, **save_kwargs)
    output_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "image_b64": output_b64,
        "width": img.width,
        "height": img.height,
        "format": output_format,
        "output_size_bytes": len(buf.getvalue()),
    }
