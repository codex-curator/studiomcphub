"""Printify POD connector (Phase 2 stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import Manifest
from . import ConnectorBase


class PrintifyConnector(ConnectorBase):
    name = "printify"

    def export(self, manifest: Manifest, collection_path: Path) -> dict[str, Any]:
        raise NotImplementedError("Printify connector coming in Phase 2")

    def validate(self, manifest: Manifest) -> list[str]:
        issues: list[str] = []
        for fname, asset in manifest.assets.items():
            if "mockup" not in asset.stages:
                issues.append(f"{fname}: missing mockups (Printify can use custom mockups)")
        return issues
