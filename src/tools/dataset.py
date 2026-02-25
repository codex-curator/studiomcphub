"""Alexandria Aeternum dataset tools.

Proxies to the Intelligence Aeternum Data Portal API for museum artwork
metadata, images, and compliance manifests. 53K+ artworks from 7 world-class
institutions (MET, Chicago, NGA, Cleveland, Rijksmuseum, Smithsonian, Paris).
"""

import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()

_PORTAL = config.data_portal_url
_TIMEOUT = 60.0


def search_artworks(query: str, museum: str = "", limit: int = 20) -> dict:
    """Search Alexandria Aeternum dataset (FREE)."""
    params = {"q": query, "limit": min(limit, 100)}
    if museum:
        params["museum"] = museum

    response = httpx.get(
        f"{_PORTAL}/agent/search",
        params=params,
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_artwork(artifact_id: str) -> dict:
    """Get Human_Standard metadata + image for an artifact."""
    response = httpx.get(
        f"{_PORTAL}/agent/artifact/{artifact_id}",
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_artwork_oracle(artifact_id: str) -> dict:
    """Get Hybrid_Premium 111-field NEST analysis + image for an artifact."""
    response = httpx.get(
        f"{_PORTAL}/agent/artifact/{artifact_id}/oracle",
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def batch_download(dataset_id: str, quantity: int, offset: int = 0) -> dict:
    """Bulk download metadata + images (min 100)."""
    response = httpx.post(
        f"{_PORTAL}/agent/batch",
        json={
            "dataset_id": dataset_id,
            "quantity": max(quantity, 100),
            "offset": offset,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def compliance_manifest(dataset_id: str, regulation: str = "all") -> dict:
    """Get AB 2013 + EU AI Act compliance manifests (FREE)."""
    response = httpx.get(
        f"{_PORTAL}/agent/compliance/{dataset_id}",
        params={"regulation": regulation, "format": "json"},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
