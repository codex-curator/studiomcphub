"""Stage 1: Remove background → transparent PNG."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class RemoveBgStage(BaseStage):
    name = "remove_bg"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image("remove_background", image_b64)
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        stem = Path(filename).stem
        out = collection_path / "no_bg" / f"{stem}_nobg.png"
        self.client.decode_to_file(resp.result["image_b64"], out)

        # Store the no-bg image for downstream stages
        context["current_image_b64"] = resp.result["image_b64"]

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
        )
