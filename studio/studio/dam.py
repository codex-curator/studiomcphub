"""Local Digital Asset Manager — folder structure + manifest I/O."""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

from .config import StudioConfig
from .models import Asset, Manifest, StageResult


# Subdirectories created for every collection
_SUBDIRS = [
    "originals",
    "no_bg",
    "resized",
    "mockups/tshirt",
    "mockups/poster",
    "mockups/canvas",
    "mockups/phone_case",
    "mockups/mug",
    "mockups/tote_bag",
    "cmyk",
    "print_ready",
    "vector",
    "watermarked",
    "enriched",
    "preview",
]


class DAM:
    """Manages the local DAM folder tree and manifest.json."""

    def __init__(self, config: StudioConfig, project_dir: Path | None = None) -> None:
        self.root = (project_dir or Path.cwd()) / config.dam_root
        self.config = config

    # ------------------------------------------------------------------
    # Collection setup
    # ------------------------------------------------------------------

    def init_collection(self, collection: str) -> Path:
        """Create the full folder tree for a collection. Returns collection path."""
        col = self.root / collection
        for sub in _SUBDIRS:
            (col / sub).mkdir(parents=True, exist_ok=True)
        # Extra print_ready size dirs
        for ps in self.config.print_sizes:
            (col / "print_ready" / ps.name).mkdir(parents=True, exist_ok=True)
        # Seed manifest if missing
        if not (col / "manifest.json").exists():
            manifest = Manifest(collection=collection)
            self._write_manifest(col, manifest)
        return col

    # ------------------------------------------------------------------
    # Manifest I/O
    # ------------------------------------------------------------------

    def load_manifest(self, collection: str) -> Manifest:
        col = self.root / collection
        mp = col / "manifest.json"
        if mp.exists():
            data = json.loads(mp.read_text())
            return Manifest(**data)
        return Manifest(collection=collection)

    def save_manifest(self, collection: str, manifest: Manifest) -> None:
        manifest.updated_at = dt.datetime.utcnow()
        manifest.total_cost_gcx = sum(a.total_cost_gcx for a in manifest.assets.values())
        self._write_manifest(self.root / collection, manifest)

    def _write_manifest(self, col: Path, manifest: Manifest) -> None:
        mp = col / "manifest.json"
        mp.write_text(manifest.model_dump_json(indent=2))

    # ------------------------------------------------------------------
    # Asset operations
    # ------------------------------------------------------------------

    def ingest_original(self, collection: str, src: Path) -> Asset:
        """Copy an image into originals/ and register in manifest."""
        col = self.init_collection(collection)
        dest = col / "originals" / src.name
        shutil.copy2(src, dest)
        asset = Asset(
            filename=src.name,
            original_path=str(dest),
            collection=collection,
        )
        manifest = self.load_manifest(collection)
        manifest.assets[src.name] = asset
        self.save_manifest(collection, manifest)
        return asset

    def record_stage(
        self,
        collection: str,
        filename: str,
        result: StageResult,
    ) -> None:
        """Update an asset's stage result in the manifest."""
        manifest = self.load_manifest(collection)
        asset = manifest.assets.get(filename)
        if not asset:
            return
        asset.stages[result.stage] = result
        asset.total_cost_gcx = sum(s.cost_gcx for s in asset.stages.values())
        self.save_manifest(collection, manifest)

    def collection_path(self, collection: str) -> Path:
        return self.root / collection

    def list_collections(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            d.name for d in self.root.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        )
