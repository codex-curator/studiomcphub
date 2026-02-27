"""Tests for StudioClient."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from studio.client import StudioClient
from studio.config import StudioConfig
from studio.models import ToolResponse


def test_encode_decode_roundtrip(tmp_path: Path) -> None:
    original = b"hello world"
    src = tmp_path / "input.bin"
    src.write_bytes(original)

    b64 = StudioClient.encode_file(src)
    dest = tmp_path / "output.bin"
    StudioClient.decode_to_file(b64, dest)
    assert dest.read_bytes() == original


def test_write_text_file(tmp_path: Path) -> None:
    dest = tmp_path / "sub" / "out.txt"
    StudioClient.write_text_file("svg content", dest)
    assert dest.read_text() == "svg content"
    assert dest.parent.exists()


def test_build_headers_with_wallet() -> None:
    config = StudioConfig(wallet="my-wallet")
    client = StudioClient(config)
    assert client._http.headers["authorization"] == "Bearer my-wallet"
    client.close()


def test_build_headers_without_wallet() -> None:
    config = StudioConfig(wallet=None)
    client = StudioClient(config)
    assert "authorization" not in client._http.headers
    client.close()
