"""Stage 6: Generate print-ready PDFs with bleed and crop marks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class PrintReadyStage(BaseStage):
    name = "print_ready"

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        stem = Path(filename).stem
        files: list[str] = []
        errors: list[str] = []

        for ps in self.config.print_sizes:
            extra: dict[str, Any] = {
                    "bleed_mm": ps.bleed_mm,
                    "crop_marks": True,
                    "output_format": "pdf",
                }
            # Use product_size for known sizes, custom dims for others
            known = {"a4", "a3", "letter", "poster_24x36", "poster_18x24"}
            if ps.name in known:
                extra["product_size"] = ps.name
            else:
                extra["product_size"] = "custom"
                extra["custom_width_mm"] = ps.width_mm
                extra["custom_height_mm"] = ps.height_mm

            resp = self.client.call_with_image(
                "print_ready",
                image_b64,
                extra=extra,
            )
            if resp.status == "error":
                errors.append(f"{ps.name}: {resp.error}")
                continue

            # print_ready returns file_b64, NOT image_b64
            out = collection_path / "print_ready" / ps.name / f"{stem}_{ps.name}.pdf"
            self.client.decode_to_file(resp.result["file_b64"], out)
            files.append(str(out))

        if not files:
            return StageResult(
                stage=self.name,
                status=StageStatus.failed,
                error="; ".join(errors),
            )

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=files,
            metadata={"sizes": [ps.name for ps in self.config.print_sizes]},
        )
