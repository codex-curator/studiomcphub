"""mint_nft -- NFT minting on Base L2 (Aeternum Collection) or Polygon.

Base L2 flow:
  1. Store image on Arweave via Archivus agent
  2. Build OpenSea-compatible metadata JSON
  3. Store metadata on Arweave
  4. Call AeternumCollection.mintTo() on Base mainnet
  5. Return token_id, URLs, OpenSea link

Polygon flow:
  Legacy proxy to Mintra agent (backward compatible).
"""

import base64
import json
import os

import httpx
import structlog
from web3 import Web3

from ..mcp_server.config import config

logger = structlog.get_logger()

# ABI for mintTo function only (loaded lazily from contracts/abi/)
_CONTRACT_ABI = None
_ABI_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "contracts", "abi", "AeternumCollection.json")

BASE_CHAIN_ID = 8453
BASE_EXPLORER = "https://basescan.org"
OPENSEA_BASE_URL = "https://opensea.io/assets/base"


def _load_abi() -> list:
    global _CONTRACT_ABI
    if _CONTRACT_ABI is None:
        with open(_ABI_PATH) as f:
            _CONTRACT_ABI = json.load(f)
    return _CONTRACT_ABI


def _store_on_arweave(data: bytes, content_type: str = "image/png") -> str:
    """Store data on Arweave via Archivus agent. Returns arweave URL."""
    data_b64 = base64.b64encode(data).decode("ascii")
    response = httpx.post(
        f"{config.archivus_url}/store",
        json={"data": data_b64, "content_type": content_type},
        timeout=120.0,
    )
    response.raise_for_status()
    result = response.json()
    tx_id = result.get("tx_id") or result.get("arweave_tx_id")
    return f"https://arweave.net/{tx_id}"


def _mint_on_base(recipient: str, metadata_uri: str) -> dict:
    """Call AeternumCollection.mintTo() on Base mainnet."""
    w3 = Web3(Web3.HTTPProvider(config.base_rpc_url))
    if not w3.is_connected():
        raise ConnectionError("Cannot connect to Base RPC")

    abi = _load_abi()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(config.base_contract_address),
        abi=abi,
    )

    minter_key = config.minter_private_key
    if not minter_key:
        raise ValueError("MINTER_PRIVATE_KEY not configured")

    account = w3.eth.account.from_key(minter_key)
    recipient_addr = Web3.to_checksum_address(recipient)

    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.mintTo(recipient_addr, metadata_uri).build_transaction({
        "chainId": BASE_CHAIN_ID,
        "from": account.address,
        "nonce": nonce,
        "gas": 200_000,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(0.001, "gwei"),
    })

    signed = w3.eth.account.sign_transaction(tx, minter_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    # Extract tokenId from Transfer event
    token_id = None
    transfer_topic = w3.keccak(text="Transfer(address,address,uint256)")
    for log in receipt.logs:
        if log.topics and log.topics[0] == transfer_topic:
            token_id = int(log.topics[3].hex(), 16)
            break

    return {
        "token_id": token_id,
        "tx_hash": receipt.transactionHash.hex(),
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
    }


def _mint_polygon_legacy(image_b64: str, metadata: dict, collection: str | None) -> dict:
    """Legacy Polygon minting via Mintra agent proxy."""
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


def mint_nft(
    image_b64: str,
    metadata: dict | None = None,
    collection: str | None = None,
    recipient_wallet: str | None = None,
    chain: str = "base",
    title: str | None = None,
    description: str | None = None,
    attributes: list[dict] | None = None,
) -> dict:
    """Mint an NFT on Base L2 or Polygon.

    Args:
        image_b64: Base64-encoded image.
        metadata: Golden Codex metadata (optional).
        collection: Collection name (Polygon only).
        recipient_wallet: EVM wallet to receive the NFT.
        chain: 'base' or 'polygon'.
        title: NFT title.
        description: NFT description.
        attributes: OpenSea-compatible trait attributes.

    Returns:
        dict with token_id, contract_address, tx_hash, URLs.
    """
    if chain == "polygon":
        logger.info("mint_nft: polygon legacy path", collection=collection)
        return _mint_polygon_legacy(image_b64, metadata or {}, collection)

    # --- Base L2 minting flow ---
    if not recipient_wallet:
        raise ValueError("recipient_wallet is required for Base minting")

    logger.info("mint_nft: base L2", recipient=recipient_wallet, title=title)

    # 1. Store image on Arweave
    image_bytes = base64.b64decode(image_b64)
    content_type = "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        content_type = "image/jpeg"
    arweave_image_url = _store_on_arweave(image_bytes, content_type)

    # 2. Build OpenSea-compatible metadata
    nft_metadata = {
        "name": title or "Aeternum Artwork",
        "description": description or "Created via StudioMCPHub — Aeternum Collection",
        "image": arweave_image_url,
        "external_url": "https://golden-codex.com",
    }
    if attributes:
        nft_metadata["attributes"] = attributes
    if metadata:
        # Include Golden Codex provenance data
        nft_metadata["properties"] = {"golden_codex": metadata}

    # 3. Store metadata on Arweave
    metadata_bytes = json.dumps(nft_metadata, indent=2).encode("utf-8")
    arweave_metadata_url = _store_on_arweave(metadata_bytes, "application/json")

    # 4. Mint on Base
    mint_result = _mint_on_base(recipient_wallet, arweave_metadata_url)
    token_id = mint_result["token_id"]
    contract_addr = config.base_contract_address

    return {
        "token_id": token_id,
        "contract_address": contract_addr,
        "tx_hash": mint_result["tx_hash"],
        "chain": "base",
        "arweave_image_url": arweave_image_url,
        "arweave_metadata_url": arweave_metadata_url,
        "opensea_url": f"{OPENSEA_BASE_URL}/{contract_addr}/{token_id}" if token_id else None,
        "explorer_url": f"{BASE_EXPLORER}/tx/0x{mint_result['tx_hash']}",
        "gas_used": mint_result["gas_used"],
    }
