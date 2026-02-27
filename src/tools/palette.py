"""extract_palette -- Extract dominant color palette from an image.

Uses Pillow's quantize() for K-means color extraction. No numpy needed.
"""

import base64
import colorsys
import io
import logging

from PIL import Image

logger = logging.getLogger("studiomcphub.tools.palette")

MAX_INPUT_BYTES = 20 * 1024 * 1024

# CSS color name approximations for common hues
_CSS_NAMES = {
    "red": (255, 0, 0), "maroon": (128, 0, 0), "orange": (255, 165, 0),
    "yellow": (255, 255, 0), "olive": (128, 128, 0), "green": (0, 128, 0),
    "lime": (0, 255, 0), "teal": (0, 128, 128), "cyan": (0, 255, 255),
    "blue": (0, 0, 255), "navy": (0, 0, 128), "purple": (128, 0, 128),
    "magenta": (255, 0, 255), "pink": (255, 192, 203), "brown": (139, 69, 19),
    "white": (255, 255, 255), "silver": (192, 192, 192), "gray": (128, 128, 128),
    "black": (0, 0, 0), "coral": (255, 127, 80), "gold": (255, 215, 0),
    "indigo": (75, 0, 130), "violet": (238, 130, 238), "beige": (245, 245, 220),
    "ivory": (255, 255, 240), "khaki": (240, 230, 140), "lavender": (230, 230, 250),
    "salmon": (250, 128, 114), "tan": (210, 180, 140), "turquoise": (64, 224, 208),
}


def _closest_css_name(r: int, g: int, b: int) -> str:
    best_name = "unknown"
    best_dist = float("inf")
    for name, (cr, cg, cb) in _CSS_NAMES.items():
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return round(h * 360), round(s * 100), round(l * 100)


def _complementary_hex(hex_color: str) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"#{255 - r:02x}{255 - g:02x}{255 - b:02x}"


def extract_palette(
    image_b64: str,
    num_colors: int = 6,
    fmt: str = "hex",
) -> dict:
    """Extract dominant color palette from an image.

    Args:
        image_b64: Base64-encoded image.
        num_colors: Number of colors to extract (3-12).
        fmt: Output format: 'hex', 'rgb', or 'hsl'.

    Returns:
        dict with colors list, dominant_color, complementary_colors.
    """
    if not 3 <= num_colors <= 12:
        raise ValueError(f"num_colors must be 3-12. Got {num_colors}.")
    if fmt not in ("hex", "rgb", "hsl"):
        raise ValueError(f"Invalid format '{fmt}'. Use: hex, rgb, hsl.")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    img = Image.open(io.BytesIO(raw)).convert("RGB")
    logger.info("extract_palette: %dx%d, %d colors, format=%s", img.width, img.height, num_colors, fmt)

    if img.width < 4 or img.height < 4:
        raise ValueError(f"Image too small ({img.width}x{img.height}). Minimum 4x4 pixels for palette extraction.")

    # Resize to 256x256 for speed
    img = img.resize((256, 256), Image.LANCZOS)

    # Quantize to extract dominant colors
    quantized = img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    palette_data = quantized.getpalette()
    pixel_counts = quantized.histogram()[:num_colors]
    total_pixels = sum(pixel_counts)

    colors = []
    for i in range(num_colors):
        r, g, b = palette_data[i * 3], palette_data[i * 3 + 1], palette_data[i * 3 + 2]
        pct = round((pixel_counts[i] / total_pixels) * 100, 1) if total_pixels > 0 else 0

        color_entry = {
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "rgb": {"r": r, "g": g, "b": b},
            "hsl": dict(zip(("h", "s", "l"), _rgb_to_hsl(r, g, b))),
            "percentage": pct,
            "css_name": _closest_css_name(r, g, b),
        }

        if fmt == "hex":
            color_entry["value"] = color_entry["hex"]
        elif fmt == "rgb":
            color_entry["value"] = f"rgb({r}, {g}, {b})"
        else:
            h, s, l = _rgb_to_hsl(r, g, b)
            color_entry["value"] = f"hsl({h}, {s}%, {l}%)"

        colors.append(color_entry)

    # Sort by percentage descending
    colors.sort(key=lambda c: c["percentage"], reverse=True)

    dominant = colors[0]["hex"]
    complementary = [_complementary_hex(c["hex"]) for c in colors[:3]]

    return {
        "colors": colors,
        "num_colors": num_colors,
        "dominant_color": dominant,
        "complementary_colors": complementary,
        "format": fmt,
    }
