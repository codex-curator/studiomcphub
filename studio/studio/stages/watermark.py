"""Stage 8: Embed invisible watermark."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class WatermarkStage(BaseStage):
    name = "watermark"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image(
            "watermark_embed",
            image_b64,
            extra={"payload": self.config.watermark_text},
        )
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        stem = Path(filename).stem
        out = collection_path / "watermarked" / f"{stem}_wm.png"
        self.client.decode_to_file(resp.result["image_b64"], out)
        context["current_image_b64"] = resp.result["image_b64"]

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
            metadata={"watermark_text": self.config.watermark_text},
        )
