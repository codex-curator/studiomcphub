"""watermark -- DCT-domain invisible watermarking (embed + detect).

Encodes/decodes a text payload into mid-frequency DCT coefficients
of the image's luminance channel (YCbCr). Imperceptible to the human eye.
"""

import base64
import io
import logging
import math

import numpy as np
from PIL import Image

logger = logging.getLogger("studiomcphub.tools.watermark")

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_PAYLOAD_CHARS = 256
BLOCK_SIZE = 8
MAGIC = b"SMHW"  # StudioMCPHub Watermark magic bytes


def _text_to_bits(text: str) -> list[int]:
    """Convert text string to list of bits."""
    data = MAGIC + len(text).to_bytes(2, "big") + text.encode("utf-8")
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_text(bits: list[int]) -> str | None:
    """Convert list of bits back to text. Returns None if magic/integrity check fails."""
    if len(bits) < (len(MAGIC) + 2) * 8:
        return None

    # Convert bits to bytes
    data = bytearray()
    for i in range(0, len(bits), 8):
        if i + 8 > len(bits):
            break
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        data.append(byte)

    # Check magic
    if bytes(data[:len(MAGIC)]) != MAGIC:
        return None

    # Extract length
    text_len = int.from_bytes(data[len(MAGIC):len(MAGIC) + 2], "big")
    start = len(MAGIC) + 2
    if start + text_len > len(data):
        return None

    try:
        return data[start:start + text_len].decode("utf-8")
    except UnicodeDecodeError:
        return None


def _dct_2d(block: np.ndarray) -> np.ndarray:
    """Compute 2D DCT of an 8x8 block."""
    from scipy.fft import dctn
    return dctn(block, type=2, norm="ortho")


def _idct_2d(block: np.ndarray) -> np.ndarray:
    """Compute 2D inverse DCT of an 8x8 block."""
    from scipy.fft import idctn
    return idctn(block, type=2, norm="ortho")


# Mid-frequency DCT coefficient positions (zigzag order positions 10-25)
MID_FREQ_POSITIONS = [
    (1, 3), (2, 2), (3, 1), (0, 4), (1, 4),
    (2, 3), (3, 2), (4, 1), (4, 0), (3, 3),
    (2, 4), (4, 2), (3, 4), (4, 3), (4, 4),
    (5, 0),
]


def watermark_embed(
    image_b64: str,
    payload: str,
    strength: float = 0.5,
) -> dict:
    """Embed an invisible watermark into an image using DCT.

    Args:
        image_b64: Base64-encoded image.
        payload: Text payload to embed (max 256 chars).
        strength: Embedding strength (0.1-1.0). Higher = more robust but more visible.

    Returns:
        dict with image_b64, payload_embedded, strength.
    """
    if not payload or len(payload) > MAX_PAYLOAD_CHARS:
        raise ValueError(f"Payload must be 1-{MAX_PAYLOAD_CHARS} characters. Got {len(payload) if payload else 0}.")
    if not 0.1 <= strength <= 1.0:
        raise ValueError(f"Strength must be 0.1-1.0. Got {strength}.")

    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    img = Image.open(io.BytesIO(raw)).convert("YCbCr")
    y_channel = np.array(img)[:, :, 0].astype(np.float64)
    h, w = y_channel.shape

    bits = _text_to_bits(payload)
    logger.info("watermark_embed: %dx%d, payload=%d chars, %d bits, strength=%.2f", w, h, len(payload), len(bits), strength)

    # Number of usable 8x8 blocks
    blocks_h = h // BLOCK_SIZE
    blocks_w = w // BLOCK_SIZE
    total_capacity = blocks_h * blocks_w * len(MID_FREQ_POSITIONS)

    if len(bits) > total_capacity:
        raise ValueError(f"Image too small for payload. Capacity: {total_capacity // 8} bytes, need: {len(bits) // 8} bytes.")

    # Embed bits across blocks
    bit_idx = 0
    scale = strength * 25  # Scale factor for coefficient modification

    for by in range(blocks_h):
        for bx in range(blocks_w):
            if bit_idx >= len(bits):
                break
            block = y_channel[by * BLOCK_SIZE:(by + 1) * BLOCK_SIZE,
                              bx * BLOCK_SIZE:(bx + 1) * BLOCK_SIZE].copy()
            dct = _dct_2d(block)

            for pos in MID_FREQ_POSITIONS:
                if bit_idx >= len(bits):
                    break
                bit = bits[bit_idx]
                coeff = dct[pos]
                # Quantize coefficient to embed bit
                quantized = round(coeff / scale)
                if quantized % 2 != bit:
                    quantized += 1 if bit == 1 else -1
                dct[pos] = quantized * scale
                bit_idx += 1

            y_channel[by * BLOCK_SIZE:(by + 1) * BLOCK_SIZE,
                       bx * BLOCK_SIZE:(bx + 1) * BLOCK_SIZE] = _idct_2d(dct)

    # Reconstruct image
    img_array = np.array(img)
    img_array[:, :, 0] = np.clip(y_channel, 0, 255).astype(np.uint8)
    result = Image.fromarray(img_array, mode="YCbCr").convert("RGB")

    buf = io.BytesIO()
    result.save(buf, format="PNG", optimize=True)
    output_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "image_b64": output_b64,
        "payload_embedded": payload,
        "strength": strength,
        "bits_embedded": len(bits),
        "width": w,
        "height": h,
        "output_size_bytes": len(buf.getvalue()),
    }


def watermark_detect(
    image_b64: str,
) -> dict:
    """Detect and extract a DCT watermark from an image.

    Args:
        image_b64: Base64-encoded image.

    Returns:
        dict with payload_detected (str or null), confidence (float).
    """
    raw = base64.b64decode(image_b64)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"Image too large ({len(raw)} bytes). Max {MAX_INPUT_BYTES // (1024*1024)}MB.")

    img = Image.open(io.BytesIO(raw)).convert("YCbCr")
    y_channel = np.array(img)[:, :, 0].astype(np.float64)
    h, w = y_channel.shape

    logger.info("watermark_detect: %dx%d", w, h)

    blocks_h = h // BLOCK_SIZE
    blocks_w = w // BLOCK_SIZE

    # Extract bits from all blocks
    bits = []
    # We need at least magic + length header = (4 + 2) * 8 = 48 bits
    max_bits_needed = (len(MAGIC) + 2 + MAX_PAYLOAD_CHARS) * 8
    scale_candidates = [s * 25 for s in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]]

    best_payload = None
    best_confidence = 0.0

    for scale in scale_candidates:
        bits = []
        for by in range(blocks_h):
            for bx in range(blocks_w):
                if len(bits) >= max_bits_needed:
                    break
                block = y_channel[by * BLOCK_SIZE:(by + 1) * BLOCK_SIZE,
                                  bx * BLOCK_SIZE:(bx + 1) * BLOCK_SIZE].copy()
                dct = _dct_2d(block)

                for pos in MID_FREQ_POSITIONS:
                    if len(bits) >= max_bits_needed:
                        break
                    coeff = dct[pos]
                    quantized = round(coeff / scale)
                    bits.append(quantized % 2)

        text = _bits_to_text(bits)
        if text is not None:
            confidence = min(1.0, 0.7 + 0.3 * (len(text) / MAX_PAYLOAD_CHARS))
            if confidence > best_confidence:
                best_payload = text
                best_confidence = confidence

    return {
        "payload_detected": best_payload,
        "confidence": round(best_confidence, 3),
        "watermark_found": best_payload is not None,
    }
