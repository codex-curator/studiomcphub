"""Shared fixtures for Studio tests."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from studio.client import StudioClient
from studio.config import StudioConfig
from studio.dam import DAM
from studio.models import ToolResponse


# 1x1 red PNG (minimal valid image)
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
TINY_PNG_B64 = base64.b64encode(_TINY_PNG).decode()


@pytest.fixture
def config() -> StudioConfig:
    return StudioConfig(
        api_url="https://test.example.com/api/tools",
        wallet="test-wallet",
        stages=["remove_bg", "palette", "resize"],
    )


@pytest.fixture
def tmp_project(tmp_path: Path, config: StudioConfig) -> Path:
    """Create a temporary project dir with studio.json."""
    cfg_path = tmp_path / "studio.json"
    cfg_path.write_text(config.model_dump_json())
    return tmp_path


@pytest.fixture
def dam(config: StudioConfig, tmp_project: Path) -> DAM:
    return DAM(config, tmp_project)


@pytest.fixture
def test_image(tmp_path: Path) -> Path:
    """Write a tiny PNG to a temp file."""
    p = tmp_path / "test.png"
    p.write_bytes(_TINY_PNG)
    return p


def make_ok_response(result: dict | None = None) -> ToolResponse:
    return ToolResponse(
        status="ok",
        result=result or {"image_b64": TINY_PNG_B64},
    )


def make_error_response(msg: str = "test error") -> ToolResponse:
    return ToolResponse(status="error", error=msg)
