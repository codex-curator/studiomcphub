"""convert_color_profile -- Convert images between sRGB and CMYK color profiles.

Uses Pillow's ImageCms module for ICC profile-based color conversion.
"""

import base64
import io
import logging

from PIL import Image, ImageCms

logger = logging.getLogger("studiomcphub.tools.color_profile")

MAX_INPUT_BYTES = 20 * 1024 * 1024


def convert_color_profile(
    image_b64: str,
    target_profile: str = "cmyk",
    dpi: int = 300,
) -> dict:
    """Convert an image's color profile.

    Args:
        image_b64: Base64-encoded image.
        target_profile: Target profile ('cmyk' or 'srgb'). Default 'cmyk'.
        dpi: Output DPI (72-1200). Default 300.

    Returns:
        dict with image_b64, profile, color_mode, dpi, format.
    """
    if target_profile not in ("cmyk", "srgb"):
        raise ValueError(f"Invalid target_profile '{target_profile}'. Use: cmyk, srgb.")
    if not 72 <= dpi <= 1200:
        raise ValueError(f"DPI must be 72-1200. Got {dpi}.")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    img = Image.open(io.BytesIO(raw))
    logger.info("convert_color_profile: %dx%d mode=%s -> %s dpi=%d",
                img.width, img.height, img.mode, target_profile, dpi)

    # Create ICC profiles
    srgb_profile = ImageCms.createProfile("sRGB")

    if target_profile == "cmyk":
        # Convert to CMYK via direct mode conversion (Pillow built-in)
        # For production-grade CMYK, bundle a proper ICC profile.
        # This uses Pillow's internal RGB->CMYK conversion.
        if img.mode == "CMYK":
            result = img
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            result = img.convert("CMYK")

        output_format = "tiff"
        color_mode = "CMYK"
    else:
        # Convert to sRGB
        if img.mode == "CMYK":
            result = img.convert("RGB")
        elif img.mode != "RGB":
            result = img.convert("RGB")
        else:
            result = img

        # Apply sRGB profile
        srgb_cms = ImageCms.ImageCmsProfile(srgb_profile)
        ImageCms.profileToProfile(result, srgb_cms, srgb_cms, inPlace=True)

        output_format = "png"
        color_mode = "RGB"

    buf = io.BytesIO()
    if output_format == "tiff":
        result.save(buf, format="TIFF", dpi=(dpi, dpi), compression="tiff_lzw")
    else:
        result.save(buf, format="PNG", optimize=True, dpi=(dpi, dpi))

    output_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "image_b64": output_b64,
        "profile": target_profile,
        "color_mode": color_mode,
        "dpi": dpi,
        "format": output_format,
        "width": result.width,
        "height": result.height,
        "output_size_bytes": len(buf.getvalue()),
    }
