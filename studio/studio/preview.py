"""HTML gallery preview generator."""

from __future__ import annotations

import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .dam import DAM
from .models import Manifest

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _file_to_data_uri(path: str) -> str:
    """Convert a local file to a base64 data URI for inline HTML display."""
    p = Path(path)
    if not p.exists():
        return ""
    suffix = p.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def generate_preview(
    dam: DAM,
    collection: str,
    output_dir: Path | None = None,
) -> Path:
    """Generate an HTML gallery for a collection. Returns path to HTML file."""
    manifest = dam.load_manifest(collection)
    col_path = dam.collection_path(collection)
    out_dir = output_dir or col_path / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["data_uri"] = _file_to_data_uri
    template = env.get_template("gallery.html")

    html = template.render(
        collection=collection,
        manifest=manifest,
        assets=manifest.assets,
    )

    out_path = out_dir / "gallery.html"
    out_path.write_text(html)
    return out_path
