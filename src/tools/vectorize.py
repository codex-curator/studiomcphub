"""vectorize_image -- Convert raster images to SVG vector format.

Uses vtracer Python bindings for high-quality vectorization.
"""

import base64
import io
import logging

from PIL import Image

logger = logging.getLogger("studiomcphub.tools.vectorize")

MAX_INPUT_BYTES = 20 * 1024 * 1024


def vectorize_image(
    image_b64: str,
    color_precision: int = 6,
    filter_speckle: int = 4,
    mode: str = "color",
) -> dict:
    """Convert a raster image to SVG vector format.

    Args:
        image_b64: Base64-encoded image.
        color_precision: Color clustering precision (1-10). Higher = more colors. Default 6.
        filter_speckle: Speckle filter size (0-100). Higher = fewer small artifacts. Default 4.
        mode: Vectorization mode ('color' or 'binary'). Default 'color'.

    Returns:
        dict with svg_content, width, height, path_count, size_bytes.
    """
    if not 1 <= color_precision <= 10:
        raise ValueError(f"color_precision must be 1-10. Got {color_precision}.")
    if not 0 <= filter_speckle <= 100:
        raise ValueError(f"filter_speckle must be 0-100. Got {filter_speckle}.")
    if mode not in ("color", "binary"):
        raise ValueError(f"Invalid mode '{mode}'. Use: color, binary.")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    # Lazy import
    import vtracer

    img = Image.open(io.BytesIO(raw))
    w, h = img.size

    logger.info("vectorize_image: %dx%d mode=%s precision=%d speckle=%d", w, h, mode, color_precision, filter_speckle)

    # vtracer expects raw image bytes (PNG format) with img_format hint
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    colormode = "color" if mode == "color" else "binary"
    svg_content = vtracer.convert_raw_image_to_svg(
        png_bytes,
        img_format="png",
        colormode=colormode,
        color_precision=color_precision,
        filter_speckle=filter_speckle,
    )

    # Count paths in SVG
    path_count = svg_content.count("<path")

    return {
        "svg_content": svg_content,
        "width": w,
        "height": h,
        "path_count": path_count,
        "size_bytes": len(svg_content.encode("utf-8")),
        "mode": mode,
        "color_precision": color_precision,
        "filter_speckle": filter_speckle,
    }
