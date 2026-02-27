"""Stage 7: Vectorize image to SVG."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class VectorizeStage(BaseStage):
    name = "vectorize"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image("vectorize_image", image_b64)
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        stem = Path(filename).stem
        out = collection_path / "vector" / f"{stem}.svg"

        # vectorize returns svg_content (raw text, NOT base64)
        self.client.write_text_file(resp.result["svg_content"], out)

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
        )
