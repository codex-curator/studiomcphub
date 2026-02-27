"""Tests for DAM manager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from studio.config import StudioConfig
from studio.dam import DAM
from studio.models import Manifest, StageResult, StageStatus


def test_init_collection_creates_dirs(dam: DAM) -> None:
    col_path = dam.init_collection("test-col")
    assert (col_path / "originals").is_dir()
    assert (col_path / "no_bg").is_dir()
    assert (col_path / "mockups" / "tshirt").is_dir()
    assert (col_path / "vector").is_dir()
    assert (col_path / "manifest.json").exists()


def test_init_collection_idempotent(dam: DAM) -> None:
    dam.init_collection("test-col")
    dam.init_collection("test-col")  # no error
    manifest = dam.load_manifest("test-col")
    assert manifest.collection == "test-col"


def test_ingest_original(dam: DAM, test_image: Path) -> None:
    asset = dam.ingest_original("col1", test_image)
    assert asset.filename == "test.png"
    assert asset.collection == "col1"
    assert Path(asset.original_path).exists()

    manifest = dam.load_manifest("col1")
    assert "test.png" in manifest.assets


def test_record_stage(dam: DAM, test_image: Path) -> None:
    dam.ingest_original("col1", test_image)
    result = StageResult(
        stage="remove_bg",
        status=StageStatus.completed,
        files=["dam/col1/no_bg/test_nobg.png"],
        cost_gcx=0.0,
    )
    dam.record_stage("col1", "test.png", result)

    manifest = dam.load_manifest("col1")
    assert "remove_bg" in manifest.assets["test.png"].stages
    assert manifest.assets["test.png"].stages["remove_bg"].status == StageStatus.completed


def test_list_collections(dam: DAM, test_image: Path) -> None:
    dam.ingest_original("alpha", test_image)
    dam.ingest_original("beta", test_image)
    assert dam.list_collections() == ["alpha", "beta"]
