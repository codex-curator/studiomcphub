"""Stage 4: Generate product mockups (PAID — 1 GCX per product)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class MockupStage(BaseStage):
    name = "mockup"
    paid = True

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

        for product in self.config.mockup_products:
            resp = self.client.call_with_image(
                "mockup_image",
                image_b64,
                extra={"product": product},
            )
            if resp.status == "error":
                errors.append(f"{product}: {resp.error}")
                continue

            out = collection_path / "mockups" / product / f"{stem}_{product}.png"
            self.client.decode_to_file(resp.result["image_b64"], out)
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
            metadata={"products": len(files), "errors": errors},
            cost_gcx=float(len(files)),  # 1 GCX per mockup
        )
