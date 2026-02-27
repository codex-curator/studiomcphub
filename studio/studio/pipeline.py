"""Multi-stage pipeline orchestrator."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Callable

from .client import StudioClient
from .config import StudioConfig
from .dam import DAM
from .models import Asset, StageResult, StageStatus
from .stages import STAGE_REGISTRY, get_stage


class Pipeline:
    """Orchestrates the image processing pipeline through configured stages."""

    def __init__(
        self,
        config: StudioConfig,
        client: StudioClient,
        dam: DAM,
        on_stage_complete: Callable[[str, str, StageResult], None] | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.dam = dam
        self.on_stage_complete = on_stage_complete

    def process(
        self,
        image_path: Path,
        collection: str,
        skip: set[str] | None = None,
    ) -> Asset:
        """Run an image through all configured stages."""
        skip = skip or set()

        # Ingest original
        asset = self.dam.ingest_original(collection, image_path)
        col_path = self.dam.collection_path(collection)
        filename = image_path.name

        # Encode the original
        image_b64 = self.client.encode_file(image_path)
        context: dict[str, Any] = {"current_image_b64": image_b64}

        for stage_name in self.config.stages:
            if stage_name in skip:
                result = StageResult(stage=stage_name, status=StageStatus.skipped)
                self.dam.record_stage(collection, filename, result)
                continue

            # Skip paid stages if no wallet configured
            stage_cls = get_stage(stage_name)
            if stage_cls.paid and not self.config.wallet:
                result = StageResult(
                    stage=stage_name,
                    status=StageStatus.skipped,
                    metadata={"reason": "no wallet configured"},
                )
                self.dam.record_stage(collection, filename, result)
                continue

            stage = stage_cls(self.client, self.config)

            # Use the latest processed image (downstream stages benefit from prior work)
            current_b64 = context.get("current_image_b64", image_b64)

            result = stage.run(current_b64, col_path, filename, context)
            self.dam.record_stage(collection, filename, result)

            if self.on_stage_complete:
                self.on_stage_complete(filename, stage_name, result)

            if result.status == StageStatus.failed:
                # Continue to next stage on failure — don't block the pipeline
                pass

        # Reload final state
        manifest = self.dam.load_manifest(collection)
        return manifest.assets.get(filename, asset)

    def process_batch(
        self,
        folder: Path,
        collection: str,
        skip: set[str] | None = None,
    ) -> list[Asset]:
        """Process all images in a folder."""
        exts = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}
        images = sorted(f for f in folder.iterdir() if f.suffix.lower() in exts)
        return [self.process(img, collection, skip) for img in images]
