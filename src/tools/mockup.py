"""mockup_image -- Composite design onto product mockup templates.

Uses Pillow compositing with programmatically-generated product outlines.
No binary template files needed -- all geometry defined in code.
"""

import base64
import io
import logging

from PIL import Image, ImageDraw

logger = logging.getLogger("studiomcphub.tools.mockup")

MAX_INPUT_BYTES = 20 * 1024 * 1024

# Product template specs: (canvas_w, canvas_h, design_region (x, y, w, h))
PRODUCTS = {
    "tshirt": {
        "canvas": (800, 900),
        "design": (225, 200, 350, 350),
        "label": "T-Shirt",
    },
    "poster": {
        "canvas": (700, 1000),
        "design": (75, 75, 550, 850),
        "label": "Poster",
    },
    "canvas": {
        "canvas": (900, 700),
        "design": (100, 50, 700, 600),
        "label": "Canvas Print",
    },
    "phone_case": {
        "canvas": (400, 800),
        "design": (50, 120, 300, 500),
        "label": "Phone Case",
    },
    "mug": {
        "canvas": (800, 600),
        "design": (200, 100, 400, 350),
        "label": "Mug",
    },
    "tote_bag": {
        "canvas": (700, 800),
        "design": (125, 150, 450, 450),
        "label": "Tote Bag",
    },
}


def _draw_product_outline(draw: ImageDraw.ImageDraw, product: str, spec: dict):
    """Draw a simple product outline on the canvas."""
    cw, ch = spec["canvas"]
    dx, dy, dw, dh = spec["design"]

    if product == "tshirt":
        # T-shirt silhouette
        draw.polygon([
            (200, 50), (300, 0), (500, 0), (600, 50),  # shoulders
            (700, 150), (600, 200), (600, 850),  # right arm, body
            (200, 850), (200, 200), (100, 150),  # left body, arm
        ], outline="#444444", width=2)
        # Collar
        draw.arc([(330, -20), (470, 80)], 0, 180, fill="#444444", width=2)

    elif product == "poster":
        # Simple frame
        draw.rectangle([(40, 40), (660, 960)], outline="#333333", width=3)
        # Shadow
        draw.line([(660, 60), (660, 960)], fill="#999999", width=4)
        draw.line([(60, 960), (660, 960)], fill="#999999", width=4)

    elif product == "canvas":
        # Canvas with depth effect
        draw.rectangle([(80, 30), (820, 670)], outline="#333333", width=2)
        # Depth lines
        draw.line([(820, 30), (850, 10)], fill="#666666", width=2)
        draw.line([(820, 670), (850, 650)], fill="#666666", width=2)
        draw.line([(850, 10), (850, 650)], fill="#666666", width=2)

    elif product == "phone_case":
        # Rounded rectangle phone shape
        draw.rounded_rectangle([(30, 20), (370, 780)], radius=30, outline="#333333", width=3)
        # Camera notch
        draw.ellipse([(170, 40), (230, 60)], outline="#555555", width=2)

    elif product == "mug":
        # Mug body
        draw.rectangle([(150, 80), (650, 520)], outline="#444444", width=2)
        # Handle
        draw.arc([(620, 150), (750, 450)], -90, 90, fill="#444444", width=3)
        # Bottom curve
        draw.arc([(150, 480), (650, 560)], 0, 180, fill="#444444", width=2)

    elif product == "tote_bag":
        # Bag body
        draw.rectangle([(75, 100), (625, 750)], outline="#444444", width=2)
        # Handles
        draw.arc([(175, 20), (325, 130)], 180, 360, fill="#444444", width=3)
        draw.arc([(375, 20), (525, 130)], 180, 360, fill="#444444", width=3)


def _parse_hex_color(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        raise ValueError(f"Invalid hex color: #{hex_str}")
    return int(hex_str[:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)


def mockup_image(
    image_b64: str,
    product: str = "tshirt",
    background_color: str = "#f5f5f5",
) -> dict:
    """Composite a design image onto a product mockup.

    Args:
        image_b64: Base64-encoded design image.
        product: Product type (tshirt, poster, canvas, phone_case, mug, tote_bag).
        background_color: Background hex color (default #f5f5f5).

    Returns:
        dict with image_b64 (mockup), product, width, height.
    """
    if product not in PRODUCTS:
        raise ValueError(f"Unknown product '{product}'. Options: {', '.join(PRODUCTS.keys())}")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    bg_color = _parse_hex_color(background_color)
    spec = PRODUCTS[product]
    cw, ch = spec["canvas"]
    dx, dy, dw, dh = spec["design"]

    logger.info("mockup_image: product=%s, canvas=%dx%d", product, cw, ch)

    # Create canvas
    canvas = Image.new("RGB", (cw, ch), bg_color)
    draw = ImageDraw.Draw(canvas)

    # Draw product outline
    _draw_product_outline(draw, product, spec)

    # Load and resize design to fit design region
    design = Image.open(io.BytesIO(raw)).convert("RGBA")
    design = design.resize((dw, dh), Image.LANCZOS)

    # Paste design into design region
    canvas.paste(design, (dx, dy), mask=design.split()[3])

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    output_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "image_b64": output_b64,
        "product": product,
        "product_label": spec["label"],
        "width": cw,
        "height": ch,
        "design_area": f"{dw}x{dh}",
        "output_size_bytes": len(buf.getvalue()),
    }
