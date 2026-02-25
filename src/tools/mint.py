"""mint_nft — Mintra Polygon NFT minting.

Mints an artwork as an NFT on Polygon with on-chain provenance link.
"""

import base64
import httpx
import structlog

from ..mcp_server.config import config

logger = structlog.get_logger()


def mint_nft(
    image_b64: str,
    metadata: dict,
    collection: str | None = None,
) -> dict:
    """Mint an NFT on Polygon.

    Args:
        image_b64: Base64-encoded image (PNG or JPEG).
        metadata: Golden Codex metadata for on-chain storage.
        collection: Optional collection name/ID.

    Returns:
        dict with token_id, contract_address, tx_hash, explorer_url.
    """
    logger.info("mint_nft", collection=collection)

    response = httpx.post(
        f"{config.mintra_url}/mint",
        json={
            "image": image_b64,
            "metadata": metadata,
            "collection": collection,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()

    return {
        "token_id": data.get("token_id"),
        "contract_address": data.get("contract_address"),
        "tx_hash": data.get("tx_hash"),
        "chain": "polygon",
        "explorer_url": f"https://polygonscan.com/tx/{data.get('tx_hash')}",
    }
