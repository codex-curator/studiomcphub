"""StudioMCPHub Admin Panel — /admin

Real-time dashboard for monitoring requests, payments, tool usage,
service health, Firestore data, and Cloud Logging entries.

Auth: ADMIN_SECRET env var checked via cookie or X-Admin-Token header.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests as http_requests
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    jsonify, make_response,
)
from google.cloud import firestore, logging as cloud_logging

from .config import config, PRICING

logger = logging.getLogger("studiomcphub.admin")


def _rfc3339(dt: datetime) -> str:
    """Format datetime as RFC3339 with Z suffix for Cloud Logging."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

admin_bp = Blueprint(
    "admin", __name__,
    template_folder="../../site/templates",
)

_db = None
_log_client = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(
            project=config.gcp_project,
            database=config.firestore_database,
        )
    return _db


def _get_log_client():
    global _log_client
    if _log_client is None:
        _log_client = cloud_logging.Client(project=config.gcp_project)
    return _log_client


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_admin_secret() -> str:
    secret = getattr(config, "admin_secret", "") or os.getenv("ADMIN_SECRET", "")
    return secret


def require_admin(f):
    """Decorator: checks cookie admin_token or X-Admin-Token header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = _get_admin_secret()
        if not secret:
            return jsonify({"error": "Admin not configured"}), 503

        token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token", "")
        if token != secret:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("admin.login_page"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@admin_bp.route("/admin")
@require_admin
def dashboard():
    return render_template("admin/dashboard.html", version=config.server_version)


@admin_bp.route("/admin/login", methods=["GET"])
def login_page():
    return render_template("admin/login.html")


@admin_bp.route("/admin/login", methods=["POST"])
def login_submit():
    password = request.form.get("password", "")
    secret = _get_admin_secret()
    if password == secret and secret:
        resp = make_response(redirect(url_for("admin.dashboard")))
        resp.set_cookie(
            "admin_token", password,
            max_age=86400,  # 24h
            httponly=True,
            samesite="Lax",
        )
        return resp
    return render_template("admin/login.html", error="Invalid password")


@admin_bp.route("/admin/logs")
@require_admin
def logs_page():
    return render_template("admin/logs.html", version=config.server_version)


@admin_bp.route("/admin/data")
@require_admin
def data_page():
    return render_template("admin/data.html", version=config.server_version)


# ---------------------------------------------------------------------------
# API: Stats
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/stats")
@require_admin
def api_stats():
    """Aggregate stats from Firestore collections and Cloud Logging."""
    db = _get_db()
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    stats = {}

    # --- Firestore: agent_spend (revenue, tool counts, wallets) ---
    try:

        # Get 30d spend docs (superset of 24h and 7d)
        spend_docs = list(
            db.collection("agent_spend")
            .where("timestamp", ">=", cutoff_30d)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(5000)
            .stream()
        )

        revenue_total = 0.0
        revenue_by_tool = {}
        revenue_by_day = {}
        requests_24h = 0
        requests_7d = 0
        wallets_set = set()
        tool_calls = {}

        for doc in spend_docs:
            d = doc.to_dict()
            amt = d.get("amount_usd", 0)
            tool = d.get("tool", "unknown")
            wallet = d.get("wallet", "")
            ts = d.get("timestamp")

            revenue_total += amt
            revenue_by_tool[tool] = revenue_by_tool.get(tool, 0) + amt
            wallets_set.add(wallet)
            tool_calls[tool] = tool_calls.get(tool, 0) + 1

            if ts:
                day_key = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
                revenue_by_day[day_key] = revenue_by_day.get(day_key, 0) + amt
                if ts >= cutoff_24h:
                    requests_24h += 1
                if ts >= cutoff_7d:
                    requests_7d += 1

        stats["requests_24h"] = requests_24h
        stats["requests_7d"] = requests_7d
        stats["tool_calls"] = dict(sorted(tool_calls.items(), key=lambda x: -x[1]))
        stats["revenue"] = {
            "total_usd": round(revenue_total, 2),
            "by_tool": {k: round(v, 2) for k, v in sorted(revenue_by_tool.items(), key=lambda x: -x[1])},
            "by_day": dict(sorted(revenue_by_day.items())),
        }
    except Exception as e:
        logger.warning(f"Stats: agent_spend query failed: {e}")
        stats["requests_24h"] = 0
        stats["requests_7d"] = 0
        stats["tool_calls"] = {}
        stats["revenue"] = {"total_usd": 0, "by_tool": {}, "by_day": {}}

    # --- Firestore: gcx_accounts (wallet count, tier distribution) ---
    try:
        accounts = list(db.collection("gcx_accounts").limit(1000).stream())
        tier_dist = {}
        for doc in accounts:
            d = doc.to_dict()
            tier = d.get("tier", "standard")
            tier_dist[tier] = tier_dist.get(tier, 0) + 1
        stats["wallets"] = {
            "total": len(accounts),
            "by_tier": tier_dist,
        }
    except Exception as e:
        logger.warning(f"Stats: gcx_accounts query failed: {e}")
        stats["wallets"] = {"total": 0, "by_tier": {}}

    # --- Firestore: loyalty_accounts ---
    try:
        loyalty_docs = list(db.collection("loyalty_accounts").limit(1000).stream())
        total_earned = 0.0
        total_redeemed = 0.0
        for doc in loyalty_docs:
            d = doc.to_dict()
            total_earned += d.get("lifetime_earned", 0)
            balance = d.get("balance", 0)
            total_redeemed += d.get("lifetime_earned", 0) - balance
        stats["loyalty"] = {
            "total_earned": round(total_earned, 2),
            "total_redeemed": round(max(total_redeemed, 0), 2),
        }
    except Exception as e:
        logger.warning(f"Stats: loyalty query failed: {e}")
        stats["loyalty"] = {"total_earned": 0, "total_redeemed": 0}

    # --- MCP sessions ---
    try:
        from .server import _mcp_sessions
        stats["mcp_sessions"] = len(_mcp_sessions)
    except Exception:
        stats["mcp_sessions"] = 0

    # --- Errors (from Cloud Logging, last 24h) ---
    try:
        log_client = _get_log_client()
        error_filter = (
            f'resource.type="cloud_run_revision" '
            f'AND resource.labels.service_name="studiomcphub" '
            f'AND severity>=ERROR '
            f'AND timestamp>="{_rfc3339(cutoff_24h)}"'
        )
        error_entries = list(log_client.list_entries(
            filter_=error_filter,
            order_by=cloud_logging.DESCENDING,
            max_results=100,
            resource_names=[f"projects/{config.gcp_project}"],
        ))
        stats["errors_24h"] = len(error_entries)
    except Exception as e:
        logger.warning(f"Stats: error count query failed: {e}")
        stats["errors_24h"] = 0

    return jsonify(stats)


# ---------------------------------------------------------------------------
# API: Health
# ---------------------------------------------------------------------------

def _check_service(name: str, url: str) -> dict:
    """Check a single service health endpoint."""
    try:
        start = time.time()
        resp = http_requests.get(url, timeout=5)
        latency = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            return {
                "name": name,
                "url": url,
                "status": "healthy",
                "latency_ms": latency,
                "version": body.get("version", ""),
            }
        return {"name": name, "url": url, "status": "unhealthy", "latency_ms": latency, "version": "", "http_status": resp.status_code}
    except http_requests.exceptions.Timeout:
        return {"name": name, "url": url, "status": "cold", "latency_ms": 5000, "version": ""}
    except Exception as e:
        return {"name": name, "url": url, "status": "unhealthy", "latency_ms": 0, "version": "", "error": str(e)}


@admin_bp.route("/api/admin/health")
@require_admin
def api_health():
    """Check all backend service health in parallel."""
    services = [
        ("StudioMCPHub", "https://studiomcphub.com/health"),
        ("Data Portal", f"{config.data_portal_url}/health"),
        ("Fluora MCP", "https://fluora-mcp-172867820131.us-west1.run.app/health"),
        ("ESRGAN GPU", f"{config.esrgan_url}/health"),
        ("SD 3.5 Large", f"{config.sd35_url}/health"),
        ("Nova Agent", f"{config.nova_url}/health"),
        ("Atlas Agent", f"{config.atlas_url}/health"),
        ("Archivus Agent", f"{config.archivus_url}/health"),
        ("Mintra Agent", f"{config.mintra_url}/health"),
    ]

    results = []
    with ThreadPoolExecutor(max_workers=len(services)) as executor:
        futures = {executor.submit(_check_service, name, url): name for name, url in services}
        for future in as_completed(futures):
            results.append(future.result())

    # Sort by original order
    name_order = {name: i for i, (name, _) in enumerate(services)}
    results.sort(key=lambda r: name_order.get(r["name"], 99))

    return jsonify({"services": results, "timestamp": datetime.now(timezone.utc).isoformat()})


# ---------------------------------------------------------------------------
# API: Logs
# ---------------------------------------------------------------------------

@admin_bp.route("/api/admin/logs")
@require_admin
def api_logs():
    """Fetch recent Cloud Logging entries."""
    service = request.args.get("service", "studiomcphub")
    severity = request.args.get("severity", "DEFAULT")
    limit = min(int(request.args.get("limit", "50")), 200)

    try:
        log_client = _get_log_client()
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        parts = [
            f'resource.type="cloud_run_revision"',
            f'resource.labels.service_name="{service}"',
            f'timestamp>="{_rfc3339(since)}"',
        ]
        if severity and severity != "DEFAULT":
            parts.append(f'severity>={severity}')

        filter_str = " AND ".join(parts)
        entries = list(log_client.list_entries(
            filter_=filter_str,
            order_by=cloud_logging.DESCENDING,
            max_results=limit,
            resource_names=[f"projects/{config.gcp_project}"],
        ))

        result = []
        for entry in entries:
            payload = entry.payload
            if isinstance(payload, dict):
                message = payload.get("message", payload.get("textPayload", str(payload)))
            else:
                message = str(payload) if payload else ""

            result.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                "severity": entry.severity or "DEFAULT",
                "message": message[:2000],
                "service": service,
                "log_name": entry.log_name.split("/")[-1] if entry.log_name else "",
            })

        return jsonify({"entries": result, "count": len(result)})
    except Exception as e:
        logger.error(f"Log query failed: {e}")
        return jsonify({"entries": [], "count": 0, "error": str(e)})


# ---------------------------------------------------------------------------
# API: Firestore Data Browser
# ---------------------------------------------------------------------------

BROWSABLE_COLLECTIONS = [
    "gcx_accounts", "agent_spend", "loyalty_accounts", "loyalty_events",
    "support_tickets", "gcx_transactions",
]


@admin_bp.route("/api/admin/firestore/<collection>")
@require_admin
def api_firestore_collection(collection: str):
    """List documents in a Firestore collection."""
    if collection not in BROWSABLE_COLLECTIONS:
        return jsonify({"error": f"Collection not browsable. Allowed: {BROWSABLE_COLLECTIONS}"}), 400

    limit = min(int(request.args.get("limit", "50")), 200)
    order_by = request.args.get("order_by", "")

    try:
        db = _get_db()
        query = db.collection(collection)
        if order_by:
            query = query.order_by(order_by, direction=firestore.Query.DESCENDING)
        query = query.limit(limit)

        docs = []
        for doc in query.stream():
            d = doc.to_dict()
            # Convert timestamps to ISO strings
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            d["_id"] = doc.id
            docs.append(d)

        return jsonify({"collection": collection, "documents": docs, "count": len(docs)})
    except Exception as e:
        logger.error(f"Firestore query failed: {e}")
        return jsonify({"collection": collection, "documents": [], "error": str(e)})


@admin_bp.route("/api/admin/firestore/<collection>/<doc_id>")
@require_admin
def api_firestore_document(collection: str, doc_id: str):
    """Get a single Firestore document."""
    if collection not in BROWSABLE_COLLECTIONS:
        return jsonify({"error": f"Collection not browsable. Allowed: {BROWSABLE_COLLECTIONS}"}), 400

    try:
        db = _get_db()
        doc = db.collection(collection).document(doc_id).get()
        if not doc.exists:
            return jsonify({"error": "Document not found"}), 404

        d = doc.to_dict()
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        d["_id"] = doc.id

        # List subcollections
        subcollections = [c.id for c in db.collection(collection).document(doc_id).collections()]

        return jsonify({"document": d, "subcollections": subcollections})
    except Exception as e:
        logger.error(f"Firestore doc query failed: {e}")
        return jsonify({"error": str(e)}), 500
