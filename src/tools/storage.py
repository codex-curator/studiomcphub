"""Agent storage — simple key-value asset storage tied to wallet addresses.

Agents and users can save images, metadata, and pipeline outputs for later
retrieval. Storage is organized per-wallet with a Firestore index and GCS
backend.

Free tier: 100MB per wallet, 500 assets max, 10MB per asset.
"""

import base64
import hashlib
import structlog
from datetime import datetime, timezone
from google.cloud import firestore, storage as gcs

from ..mcp_server.config import config

logger = structlog.get_logger()

STORAGE_BUCKET = "codex-agent-storage"
MAX_ASSET_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per asset (2x upscaled images are ~6MB)
MAX_ASSETS_PER_WALLET = 500
MAX_STORAGE_BYTES = 100 * 1024 * 1024   # 100MB per wallet

_db = None
_gcs = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def _get_gcs():
    global _gcs
    if _gcs is None:
        _gcs = gcs.Client(project=config.gcp_project)
    return _gcs


def _wallet_path(wallet: str, key: str) -> str:
    """GCS object path: wallets/{wallet}/{key}"""
    return f"wallets/{wallet}/{key}"


def _get_wallet_stats(wallet: str) -> dict:
    """Get current storage usage for a wallet."""
    db = _get_db()
    stats_ref = db.collection("agent_storage_stats").document(wallet)
    doc = stats_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"asset_count": 0, "total_bytes": 0}


def save_asset(wallet: str, key: str, data: str, content_type: str = "image/png",
               metadata: dict = None) -> dict:
    """Save an asset (base64 data + optional metadata) tied to a wallet.

    Args:
        wallet: EVM wallet address (lowercase).
        key: Unique key for this asset (e.g., "my-landscape", "pipeline-output-001").
        data: Base64-encoded data (image, JSON, etc.).
        content_type: MIME type (default image/png).
        metadata: Optional JSON metadata to store alongside.

    Returns:
        dict with key, size_bytes, storage_url, and wallet stats.
    """
    wallet = wallet.lower()
    key = key.strip().replace("/", "_").replace("..", "_")[:128]

    if not key:
        raise ValueError("Asset key is required")

    # Decode and validate size
    try:
        raw_bytes = base64.b64decode(data)
    except Exception:
        raise ValueError("Invalid base64 data")

    size_bytes = len(raw_bytes)
    if size_bytes > MAX_ASSET_SIZE_BYTES:
        raise ValueError(f"Asset too large: {size_bytes} bytes (max {MAX_ASSET_SIZE_BYTES})")

    # Check wallet limits
    stats = _get_wallet_stats(wallet)
    if stats["asset_count"] >= MAX_ASSETS_PER_WALLET:
        raise ValueError(f"Storage limit reached: {MAX_ASSETS_PER_WALLET} assets max per wallet")
    if stats["total_bytes"] + size_bytes > MAX_STORAGE_BYTES:
        raise ValueError(
            f"Storage quota exceeded: {stats['total_bytes'] + size_bytes} bytes "
            f"would exceed {MAX_STORAGE_BYTES} byte limit"
        )

    # Upload to GCS
    client = _get_gcs()
    bucket = client.bucket(STORAGE_BUCKET)
    blob_path = _wallet_path(wallet, key)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(raw_bytes, content_type=content_type)

    # Compute hash for integrity
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    # Index in Firestore
    db = _get_db()
    now = datetime.now(timezone.utc)

    # Check if this key already exists (update vs create)
    asset_ref = db.collection("agent_storage").document(f"{wallet}_{key}")
    existing = asset_ref.get()
    old_size = 0
    is_update = False
    if existing.exists:
        old_size = existing.to_dict().get("size_bytes", 0)
        is_update = True

    asset_ref.set({
        "wallet": wallet,
        "key": key,
        "size_bytes": size_bytes,
        "content_type": content_type,
        "sha256": sha256,
        "metadata": metadata or {},
        "gcs_path": f"gs://{STORAGE_BUCKET}/{blob_path}",
        "created_at": existing.to_dict().get("created_at", now) if existing.exists else now,
        "updated_at": now,
    })

    # Update wallet stats
    stats_ref = db.collection("agent_storage_stats").document(wallet)
    new_count = stats["asset_count"] + (0 if is_update else 1)
    new_bytes = stats["total_bytes"] - old_size + size_bytes
    stats_ref.set({
        "asset_count": new_count,
        "total_bytes": new_bytes,
        "last_updated": now,
    }, merge=True)

    logger.info("storage.save", wallet=wallet[:10], key=key, size=size_bytes)

    return {
        "key": key,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "content_type": content_type,
        "action": "updated" if is_update else "created",
        "storage_used": {
            "assets": new_count,
            "bytes": new_bytes,
            "limit_bytes": MAX_STORAGE_BYTES,
        },
    }


def get_asset(wallet: str, key: str) -> dict:
    """Retrieve a stored asset by key.

    Args:
        wallet: EVM wallet address.
        key: Asset key.

    Returns:
        dict with key, data (base64), content_type, metadata, timestamps.
    """
    wallet = wallet.lower()
    key = key.strip()

    db = _get_db()
    doc = db.collection("agent_storage").document(f"{wallet}_{key}").get()
    if not doc.exists:
        raise ValueError(f"Asset not found: {key}")

    asset = doc.to_dict()

    # Download from GCS
    client = _get_gcs()
    bucket = client.bucket(STORAGE_BUCKET)
    blob = bucket.blob(_wallet_path(wallet, key))

    if not blob.exists():
        raise ValueError(f"Asset data missing from storage: {key}")

    raw_bytes = blob.download_as_bytes()
    data_b64 = base64.b64encode(raw_bytes).decode("utf-8")

    return {
        "key": key,
        "data": data_b64,
        "content_type": asset.get("content_type", "application/octet-stream"),
        "size_bytes": asset.get("size_bytes", len(raw_bytes)),
        "sha256": asset.get("sha256", ""),
        "metadata": asset.get("metadata", {}),
        "created_at": asset["created_at"].isoformat() if hasattr(asset.get("created_at"), "isoformat") else "",
        "updated_at": asset["updated_at"].isoformat() if hasattr(asset.get("updated_at"), "isoformat") else "",
    }


def list_assets(wallet: str) -> dict:
    """List all stored assets for a wallet.

    Args:
        wallet: EVM wallet address.

    Returns:
        dict with assets list and storage stats.
    """
    wallet = wallet.lower()
    db = _get_db()

    docs = (
        db.collection("agent_storage")
        .where("wallet", "==", wallet)
        .limit(MAX_ASSETS_PER_WALLET)
        .stream()
    )

    assets = []
    for doc in docs:
        d = doc.to_dict()
        created = d.get("created_at")
        updated = d.get("updated_at")
        assets.append({
            "key": d.get("key"),
            "size_bytes": d.get("size_bytes", 0),
            "content_type": d.get("content_type", ""),
            "sha256": d.get("sha256", ""),
            "metadata": d.get("metadata", {}),
            "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
            "updated_at": updated.isoformat() if hasattr(updated, "isoformat") else str(updated or ""),
        })

    # Sort by updated_at descending (client-side to avoid composite index requirement)
    assets.sort(key=lambda a: a["updated_at"], reverse=True)

    stats = _get_wallet_stats(wallet)

    return {
        "wallet": wallet,
        "assets": assets,
        "count": len(assets),
        "storage_used": {
            "bytes": stats.get("total_bytes", 0),
            "limit_bytes": MAX_STORAGE_BYTES,
            "assets": stats.get("asset_count", 0),
            "limit_assets": MAX_ASSETS_PER_WALLET,
        },
    }


def delete_asset(wallet: str, key: str) -> dict:
    """Delete a stored asset.

    Args:
        wallet: EVM wallet address.
        key: Asset key.

    Returns:
        dict confirming deletion with updated stats.
    """
    wallet = wallet.lower()
    key = key.strip()

    db = _get_db()
    doc_ref = db.collection("agent_storage").document(f"{wallet}_{key}")
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError(f"Asset not found: {key}")

    asset = doc.to_dict()
    size_bytes = asset.get("size_bytes", 0)

    # Delete from GCS
    try:
        client = _get_gcs()
        bucket = client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(_wallet_path(wallet, key))
        blob.delete()
    except Exception as e:
        logger.warning(f"GCS delete failed (may not exist): {e}")

    # Delete Firestore index
    doc_ref.delete()

    # Update stats
    stats = _get_wallet_stats(wallet)
    stats_ref = db.collection("agent_storage_stats").document(wallet)
    new_count = max(stats["asset_count"] - 1, 0)
    new_bytes = max(stats["total_bytes"] - size_bytes, 0)
    stats_ref.set({
        "asset_count": new_count,
        "total_bytes": new_bytes,
        "last_updated": datetime.now(timezone.utc),
    }, merge=True)

    logger.info("storage.delete", wallet=wallet[:10], key=key)

    return {
        "key": key,
        "deleted": True,
        "freed_bytes": size_bytes,
        "storage_used": {
            "assets": new_count,
            "bytes": new_bytes,
            "limit_bytes": MAX_STORAGE_BYTES,
        },
    }
