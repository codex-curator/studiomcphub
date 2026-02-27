"""Stage 5: Convert to CMYK color profile for print."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class ColorProfileStage(BaseStage):
    name = "cmyk"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image(
            "convert_color_profile",
            image_b64,
            extra={"target_profile": "cmyk", "dpi": 300},
        )
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        stem = Path(filename).stem
        out = collection_path / "cmyk" / f"{stem}_cmyk.tiff"
        self.client.decode_to_file(resp.result["image_b64"], out)

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
        )
