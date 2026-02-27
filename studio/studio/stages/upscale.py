"""Stage 10: ESRGAN upscaling (PAID — 1 GCX)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class UpscaleStage(BaseStage):
    name = "upscale"
    paid = True

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image(
            "upscale_image",
            image_b64,
            extra={"model": self.config.upscale_model},
        )
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        stem = Path(filename).stem
        out = collection_path / "resized" / f"{stem}_upscaled.png"
        self.client.decode_to_file(resp.result["image_b64"], out)
        context["current_image_b64"] = resp.result["image_b64"]

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
            cost_gcx=1.0,
        )
