"""POD platform connectors (Phase 2 stubs)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import Manifest


class ConnectorBase(ABC):
    """Base class for POD platform connectors."""

    name: str = ""

    @abstractmethod
    def export(self, manifest: Manifest, collection_path: Path) -> dict[str, Any]:
        """Export a collection to the POD platform. Returns status dict."""
        ...

    @abstractmethod
    def validate(self, manifest: Manifest) -> list[str]:
        """Validate that the collection meets platform requirements. Returns list of issues."""
        ...
