"""Configuration loader — reads studio.json from the project root."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


_DEFAULT_STAGES = [
    "remove_bg",
    "palette",
    "resize",
    "mockup",
    "cmyk",
    "print_ready",
    "vectorize",
    "watermark",
    "enrich",
    "upscale",
]

_DEFAULT_MOCKUP_PRODUCTS = [
    "tshirt",
    "poster",
    "canvas",
    "phone_case",
    "mug",
    "tote_bag",
]

_DEFAULT_PRINT_SIZES = [
    {"name": "a4", "width_mm": 210, "height_mm": 297},
    {"name": "poster_24x36", "width_mm": 610, "height_mm": 914},
]


class ResizeConfig(BaseModel):
    max_width: int = 2048
    max_height: int = 2048
    format: str = "png"


class PrintSize(BaseModel):
    name: str
    width_mm: int
    height_mm: int
    bleed_mm: float = 3.0


class StudioConfig(BaseModel):
    """Top-level configuration for the Studio pipeline."""

    api_url: str = "https://studiomcphub.com/api/tools"
    wallet: str | None = None
    dam_root: str = "dam"
    stages: list[str] = Field(default_factory=lambda: list(_DEFAULT_STAGES))
    mockup_products: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_MOCKUP_PRODUCTS)
    )
    print_sizes: list[PrintSize] = Field(
        default_factory=lambda: [PrintSize(**s) for s in _DEFAULT_PRINT_SIZES]
    )
    resize: ResizeConfig = Field(default_factory=ResizeConfig)
    enrich_tier: str = "standard"
    upscale_model: str = "RealESRGAN_x4plus"
    watermark_text: str = "StudioMCPHub"
    timeout_s: int = 120
    max_retries: int = 2


def load_config(project_dir: Path | None = None) -> StudioConfig:
    """Load config from studio.json in the given directory (or cwd)."""
    root = project_dir or Path.cwd()
    config_path = root / "studio.json"
    if config_path.exists():
        data = json.loads(config_path.read_text())
        return StudioConfig(**data)
    return StudioConfig()
