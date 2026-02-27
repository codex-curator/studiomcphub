"""Tests for Pipeline orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from studio.client import StudioClient
from studio.config import StudioConfig
from studio.dam import DAM
from studio.models import StageStatus, ToolResponse
from studio.pipeline import Pipeline
from tests.conftest import TINY_PNG_B64, make_ok_response


@pytest.fixture
def mock_client(config: StudioConfig) -> MagicMock:
    client = MagicMock(spec=StudioClient)
    client.config = config
    client.encode_file.return_value = TINY_PNG_B64
    client.call_with_image.return_value = make_ok_response()
    client.decode_to_file.side_effect = lambda b64, dest: (
        dest.parent.mkdir(parents=True, exist_ok=True),
        dest.write_bytes(b"fake"),
    )
    return client


def test_process_runs_configured_stages(
    config: StudioConfig,
    mock_client: MagicMock,
    dam: DAM,
    test_image: Path,
    tmp_project: Path,
) -> None:
    pipeline = Pipeline(config, mock_client, dam)
    asset = pipeline.process(test_image, "test-col")

    assert len(asset.stages) == 3  # remove_bg, palette, resize
    for name in ["remove_bg", "palette", "resize"]:
        assert name in asset.stages


def test_process_skips_stages(
    config: StudioConfig,
    mock_client: MagicMock,
    dam: DAM,
    test_image: Path,
) -> None:
    pipeline = Pipeline(config, mock_client, dam)
    asset = pipeline.process(test_image, "test-col", skip={"palette"})

    assert asset.stages["palette"].status == StageStatus.skipped
    assert asset.stages["remove_bg"].status == StageStatus.completed


def test_process_skips_paid_without_wallet(
    mock_client: MagicMock,
    test_image: Path,
    tmp_project: Path,
) -> None:
    config = StudioConfig(
        api_url="https://test.example.com/api/tools",
        wallet=None,
        stages=["remove_bg", "enrich"],
    )
    dam = DAM(config, tmp_project)
    pipeline = Pipeline(config, mock_client, dam)
    asset = pipeline.process(test_image, "test-col")

    assert asset.stages["enrich"].status == StageStatus.skipped
    assert "no wallet" in asset.stages["enrich"].metadata.get("reason", "")


def test_callback_fires(
    config: StudioConfig,
    mock_client: MagicMock,
    dam: DAM,
    test_image: Path,
) -> None:
    calls: list[tuple] = []
    pipeline = Pipeline(
        config, mock_client, dam,
        on_stage_complete=lambda f, s, r: calls.append((f, s, r.status)),
    )
    pipeline.process(test_image, "test-col")
    assert len(calls) == 3
