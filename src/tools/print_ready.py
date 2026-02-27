"""print_ready -- Prepare images for professional printing.

Sets DPI, adds bleed margins, draws crop marks, outputs TIFF or PDF.
"""

import base64
import io
import logging
import math

from PIL import Image, ImageDraw

logger = logging.getLogger("studiomcphub.tools.print_ready")

MAX_INPUT_BYTES = 20 * 1024 * 1024

# Standard sizes in mm (width, height)
STANDARD_SIZES = {
    "a4": (210, 297),
    "a3": (297, 420),
    "letter": (216, 279),
    "poster_24x36": (610, 914),
}


def _mm_to_px(mm: float, dpi: int) -> int:
    return round(mm * dpi / 25.4)


def _draw_crop_marks(draw: ImageDraw.ImageDraw, bleed_px: int, content_w: int, content_h: int, mark_len: int = 20):
    """Draw L-shaped crop marks at the four corners of the content area."""
    mark_color = (0, 0, 0)
    mark_width = 1
    offset = 4  # Gap between mark and content edge

    corners = [
        # Top-left
        ((bleed_px - mark_len - offset, bleed_px), (bleed_px - offset, bleed_px)),
        ((bleed_px, bleed_px - mark_len - offset), (bleed_px, bleed_px - offset)),
        # Top-right
        ((bleed_px + content_w + offset, bleed_px), (bleed_px + content_w + mark_len + offset, bleed_px)),
        ((bleed_px + content_w, bleed_px - mark_len - offset), (bleed_px + content_w, bleed_px - offset)),
        # Bottom-left
        ((bleed_px - mark_len - offset, bleed_px + content_h), (bleed_px - offset, bleed_px + content_h)),
        ((bleed_px, bleed_px + content_h + offset), (bleed_px, bleed_px + content_h + mark_len + offset)),
        # Bottom-right
        ((bleed_px + content_w + offset, bleed_px + content_h), (bleed_px + content_w + mark_len + offset, bleed_px + content_h)),
        ((bleed_px + content_w, bleed_px + content_h + offset), (bleed_px + content_w, bleed_px + content_h + mark_len + offset)),
    ]

    for start, end in corners:
        draw.line([start, end], fill=mark_color, width=mark_width)


def print_ready(
    image_b64: str,
    dpi: int = 300,
    bleed_mm: float = 3.0,
    crop_marks: bool = True,
    output_format: str = "tiff",
    product_size: str = "a4",
    custom_width_mm: float | None = None,
    custom_height_mm: float | None = None,
) -> dict:
    """Prepare an image for professional printing.

    Args:
        image_b64: Base64-encoded image.
        dpi: Output DPI (150, 300, or 600).
        bleed_mm: Bleed margin in mm (0-10). Default 3mm.
        crop_marks: Whether to draw crop marks. Default True.
        output_format: Output format ('tiff' or 'pdf'). Default 'tiff'.
        product_size: Standard size ('a4', 'a3', 'letter', 'poster_24x36', 'custom').
        custom_width_mm: Width in mm (required if product_size='custom').
        custom_height_mm: Height in mm (required if product_size='custom').

    Returns:
        dict with file_b64, format, dpi, dimensions_mm, bleed_mm, file_size_bytes.
    """
    if dpi not in (150, 300, 600):
        raise ValueError(f"DPI must be 150, 300, or 600. Got {dpi}.")
    if not 0 <= bleed_mm <= 10:
        raise ValueError(f"Bleed must be 0-10mm. Got {bleed_mm}.")
    if output_format not in ("tiff", "pdf"):
        raise ValueError(f"Invalid output_format '{output_format}'. Use: tiff, pdf.")

    if product_size == "custom":
        if not custom_width_mm or not custom_height_mm:
            raise ValueError("custom_width_mm and custom_height_mm required for custom size.")
        if not (10 <= custom_width_mm <= 2000 and 10 <= custom_height_mm <= 2000):
            raise ValueError("Custom dimensions must be 10-2000mm.")
        target_w_mm, target_h_mm = custom_width_mm, custom_height_mm
    elif product_size in STANDARD_SIZES:
        target_w_mm, target_h_mm = STANDARD_SIZES[product_size]
    else:
        raise ValueError(f"Unknown product_size '{product_size}'. Options: {', '.join(STANDARD_SIZES.keys())}, custom")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    img = Image.open(io.BytesIO(raw)).convert("RGB")

    # Calculate pixel dimensions
    content_w = _mm_to_px(target_w_mm, dpi)
    content_h = _mm_to_px(target_h_mm, dpi)
    bleed_px = _mm_to_px(bleed_mm, dpi)

    logger.info("print_ready: %s %dx%dmm @ %ddpi, bleed=%gmm", product_size, target_w_mm, target_h_mm, dpi, bleed_mm)

    # Resize image to content area (cover mode - crop to fill)
    src_ratio = img.width / img.height
    dst_ratio = content_w / content_h
    if src_ratio > dst_ratio:
        new_h = content_h
        new_w = int(img.width * (content_h / img.height))
    else:
        new_w = content_w
        new_h = int(img.height * (content_w / img.width))

    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - content_w) // 2
    top = (new_h - content_h) // 2
    img = img.crop((left, top, left + content_w, top + content_h))

    # Create canvas with bleed
    total_w = content_w + 2 * bleed_px
    total_h = content_h + 2 * bleed_px
    canvas = Image.new("RGB", (total_w, total_h), (255, 255, 255))

    # Extend image into bleed area by scaling slightly larger
    if bleed_px > 0:
        bleed_img = img.resize((content_w + 2 * bleed_px, content_h + 2 * bleed_px), Image.LANCZOS)
        canvas.paste(bleed_img, (0, 0))
    else:
        canvas.paste(img, (bleed_px, bleed_px))

    # Draw crop marks
    if crop_marks and bleed_px > 0:
        draw = ImageDraw.Draw(canvas)
        _draw_crop_marks(draw, bleed_px, content_w, content_h)

    buf = io.BytesIO()
    if output_format == "tiff":
        canvas.save(buf, format="TIFF", dpi=(dpi, dpi), compression="tiff_lzw")
    else:
        # PDF output via reportlab
        from reportlab.lib.pagesizes import mm as rl_mm
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas as pdf_canvas

        pdf_buf = io.BytesIO()
        page_w = total_w * 72 / dpi  # Convert px to PDF points
        page_h = total_h * 72 / dpi
        c = pdf_canvas.Canvas(pdf_buf, pagesize=(page_w, page_h))
        img_reader = ImageReader(canvas)
        c.drawImage(img_reader, 0, 0, width=page_w, height=page_h)
        c.showPage()
        c.save()
        buf = pdf_buf

    output_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "file_b64": output_b64,
        "format": output_format,
        "dpi": dpi,
        "dimensions_mm": {"width": target_w_mm, "height": target_h_mm},
        "bleed_mm": bleed_mm,
        "crop_marks": crop_marks,
        "product_size": product_size,
        "canvas_pixels": f"{total_w}x{total_h}",
        "file_size_bytes": len(buf.getvalue()),
    }
