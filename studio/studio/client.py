"""HTTP client for the StudioMCPHub remote API."""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

import httpx

from .config import StudioConfig
from .models import ToolResponse


class StudioClient:
    """Sync HTTP client wrapping StudioMCPHub tool endpoints."""

    def __init__(self, config: StudioConfig) -> None:
        self.config = config
        self._http = httpx.Client(
            base_url=config.api_url,
            timeout=config.timeout_s,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.wallet:
            h["Authorization"] = f"Bearer {self.config.wallet}"
        return h

    # ------------------------------------------------------------------
    # Core call
    # ------------------------------------------------------------------

    def call(self, tool: str, params: dict[str, Any]) -> ToolResponse:
        """Call a StudioMCPHub tool and return parsed response."""
        last_err: Exception | None = None
        for attempt in range(1 + self.config.max_retries):
            try:
                resp = self._http.post(f"/{tool}", json=params)
                resp.raise_for_status()
                data = resp.json()
                return ToolResponse(
                    status=data.get("status", "ok"),
                    result=data.get("result", data),
                    error=data.get("error"),
                    tool=tool,
                    cost_gcx=data.get("cost_gcx"),
                )
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_err = exc
                if attempt < self.config.max_retries:
                    time.sleep(2 ** attempt)
        return ToolResponse(
            status="error",
            error=str(last_err),
            tool=tool,
        )

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def call_with_image(
        self,
        tool: str,
        image_b64: str,
        extra: dict[str, Any] | None = None,
    ) -> ToolResponse:
        """Call a tool that requires an image (base64)."""
        params: dict[str, Any] = {"image": image_b64}
        if extra:
            params.update(extra)
        return self.call(tool, params)

    def check_balance(self) -> ToolResponse:
        return self.call("check_balance", {})

    # ------------------------------------------------------------------
    # Base64 helpers
    # ------------------------------------------------------------------

    @staticmethod
    def encode_file(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode()

    @staticmethod
    def decode_to_file(b64: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(b64))
        return dest

    @staticmethod
    def write_text_file(content: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        return dest

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> StudioClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
