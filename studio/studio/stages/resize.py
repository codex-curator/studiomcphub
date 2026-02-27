"""Stage 3: Resize image to configured max dimensions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class ResizeStage(BaseStage):
    name = "resize"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image(
            "resize_image",
            image_b64,
            extra={
                "width": self.config.resize.max_width,
                "height": self.config.resize.max_height,
                "format": self.config.resize.format,
            },
        )
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        stem = Path(filename).stem
        out = collection_path / "resized" / f"{stem}_resized.{self.config.resize.format}"
        self.client.decode_to_file(resp.result["image_b64"], out)
        context["current_image_b64"] = resp.result["image_b64"]

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
            metadata=resp.result.get("dimensions", {}),
        )
