"""Printful POD connector (Phase 2 stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import Manifest
from . import ConnectorBase


class PrintfulConnector(ConnectorBase):
    name = "printful"

    def export(self, manifest: Manifest, collection_path: Path) -> dict[str, Any]:
        raise NotImplementedError("Printful connector coming in Phase 2")

    def validate(self, manifest: Manifest) -> list[str]:
        issues: list[str] = []
        for fname, asset in manifest.assets.items():
            if "remove_bg" not in asset.stages:
                issues.append(f"{fname}: missing background removal (recommended for Printful)")
        return issues
