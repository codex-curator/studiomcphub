"""Stage 2: Extract color palette (metadata only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class PaletteStage(BaseStage):
    name = "palette"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image(
            "extract_palette",
            image_b64,
            extra={"num_colors": 6, "format": "hex"},
        )
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        colors = resp.result.get("colors", [])
        context["palette"] = colors

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            metadata={"colors": colors},
        )
