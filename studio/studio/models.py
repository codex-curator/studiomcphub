"""Pydantic data models for StudioMCPHub Studio."""

from __future__ import annotations

import datetime as dt
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    skipped = "skipped"
    failed = "failed"


class ToolResponse(BaseModel):
    """Raw response from the StudioMCPHub API."""

    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    tool: str | None = None
    cost_gcx: float | None = None


class StageResult(BaseModel):
    """Result of a single pipeline stage execution."""

    stage: str
    status: StageStatus
    started_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    completed_at: dt.datetime | None = None
    duration_s: float | None = None
    files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    cost_gcx: float = 0.0


class Asset(BaseModel):
    """Single image asset tracked in the DAM."""

    filename: str
    original_path: str
    collection: str
    added_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    stages: dict[str, StageResult] = Field(default_factory=dict)
    palette: list[str] = Field(default_factory=list)
    enrichment: dict[str, Any] = Field(default_factory=dict)
    total_cost_gcx: float = 0.0


class Manifest(BaseModel):
    """DAM collection manifest persisted as manifest.json."""

    version: str = "1.0.0"
    collection: str
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    assets: dict[str, Asset] = Field(default_factory=dict)
    total_cost_gcx: float = 0.0

    def asset_count(self) -> int:
        return len(self.assets)

    def completed_count(self) -> int:
        return sum(
            1
            for a in self.assets.values()
            if all(s.status == StageStatus.completed for s in a.stages.values())
        )
