"""Pipeline stage base class and registry."""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..client import StudioClient
from ..config import StudioConfig
from ..models import StageResult, StageStatus


class BaseStage(ABC):
    """Abstract base for all pipeline stages."""

    name: str = ""
    paid: bool = False

    def __init__(self, client: StudioClient, config: StudioConfig) -> None:
        self.client = client
        self.config = config

    def run(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        """Execute the stage with timing and error handling."""
        start = dt.datetime.utcnow()
        try:
            result = self.execute(image_b64, collection_path, filename, context)
            result.started_at = start
            result.completed_at = dt.datetime.utcnow()
            result.duration_s = (result.completed_at - start).total_seconds()
            return result
        except Exception as exc:
            now = dt.datetime.utcnow()
            return StageResult(
                stage=self.name,
                status=StageStatus.failed,
                started_at=start,
                completed_at=now,
                duration_s=(now - start).total_seconds(),
                error=str(exc),
            )

    @abstractmethod
    def execute(
        self,
        image_b64: str,
        collection_path: Path,
        filename: str,
        context: dict[str, Any],
    ) -> StageResult:
        """Implement the stage logic. Return a StageResult."""
        ...


# ------------------------------------------------------------------
# Registry — import all stages and map by name
# ------------------------------------------------------------------

STAGE_REGISTRY: dict[str, type[BaseStage]] = {}


def register(cls: type[BaseStage]) -> type[BaseStage]:
    """Decorator to register a stage class."""
    STAGE_REGISTRY[cls.name] = cls
    return cls


def get_stage(name: str) -> type[BaseStage]:
    if name not in STAGE_REGISTRY:
        raise KeyError(f"Unknown stage: {name}")
    return STAGE_REGISTRY[name]


# Import all stages so decorators fire
from . import (  # noqa: E402, F401
    color_profile,
    enrich,
    mockup,
    palette,
    print_ready,
    remove_bg,
    resize,
    upscale,
    vectorize,
    watermark,
)
