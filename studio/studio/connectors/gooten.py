"""Gooten POD connector (Phase 2 stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import Manifest
from . import ConnectorBase


class GootenConnector(ConnectorBase):
    name = "gooten"

    def export(self, manifest: Manifest, collection_path: Path) -> dict[str, Any]:
        raise NotImplementedError("Gooten connector coming in Phase 2")

    def validate(self, manifest: Manifest) -> list[str]:
        issues: list[str] = []
        for fname, asset in manifest.assets.items():
            if "cmyk" not in asset.stages:
                issues.append(f"{fname}: missing CMYK conversion (required for Gooten)")
            if "resize" not in asset.stages:
                issues.append(f"{fname}: missing resize (Gooten requires min 2400x3200 for posters)")
        return issues
