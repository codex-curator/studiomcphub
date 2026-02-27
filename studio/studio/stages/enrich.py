"""Stage 9: AI metadata enrichment (PAID — 2 GCX premium / 1 GCX standard)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import StageResult, StageStatus
from . import BaseStage, register


@register
class EnrichStage(BaseStage):
    name = "enrich"
    paid = True

    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        resp = self.client.call_with_image(
            "enrich_metadata",
            image_b64,
            extra={"tier": self.config.enrich_tier},
        )
        if resp.status == "error":
            return StageResult(stage=self.name, status=StageStatus.failed, error=resp.error)

        metadata = resp.result.get("metadata", resp.result)
        context["enrichment"] = metadata

        # Save enrichment JSON
        stem = Path(filename).stem
        out = collection_path / "enriched" / f"{stem}_enriched.json"
        self.client.write_text_file(json.dumps(metadata, indent=2), out)

        cost = 2.0 if self.config.enrich_tier == "premium" else 1.0

        return StageResult(
            stage=self.name,
            status=StageStatus.completed,
            files=[str(out)],
            metadata=metadata,
            cost_gcx=cost,
        )
