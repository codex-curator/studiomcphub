# CLAUDE.md -- StudioMCPHub

**What this is**: An MCP (Model Context Protocol) server hub offering creative AI tools as paid services for autonomous AI agents and local assistants. Built by AI, for AI.

**Domain**: studiomcphub.com
**Parent company**: Metavolve Labs, Inc.
**Sibling product**: golden-codex.com (human-facing SaaS studio)
**GCP project**: `the-golden-codex-1111`
**Canonical path (WSL)**: `/mnt/c/Users/atmta/source/repos/studiomcphub.com/`
**Human partner**: Tad MacPherson (curator@golden-codex.com)

---

## Mission

> The creative infrastructure layer for the AI age.
> Every agent deserves a studio.

StudioMCPHub exposes the Golden Codex pipeline as discoverable, pay-per-call MCP tools. AI agents connect, create, and pay -- no accounts required.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   studiomcphub.com                       │
│              (Cloud Run + Streamable HTTP)               │
├─────────────────────────────────────────────────────────┤
│  MCP Server (FastMCP / Python)                          │
│  ├── generate_image     — SD 3.5 Large + T5-XXL        │
│  ├── upscale_image      — ESRGAN x4 (L4 GPU)           │
│  ├── enrich_metadata    — Nova (Gemini 2.5/3.0 Pro)    │
│  ├── infuse_metadata    — Atlas (ExifTool + XMP)        │
│  ├── register_hash      — Aegis (pHash + LSH index)    │
│  ├── store_permanent    — Archivus (Arweave L1)        │
│  ├── mint_nft           — Mintra (Polygon)             │
│  ├── verify_provenance  — Aegis (strip-proof lookup)   │
│  └── full_pipeline      — All stages, one call         │
├─────────────────────────────────────────────────────────┤
│  Payment Layer                                          │
│  ├── x402 (USDC on Base) — Agent-native, no accounts   │
│  ├── Stripe per-call     — Traditional payment rails    │
│  └── GCX Credits         — Pre-purchased token balance  │
├─────────────────────────────────────────────────────────┤
│  Discovery                                              │
│  ├── /.well-known/mcp.json  — MCP Server Card           │
│  ├── /llms.txt              — LLM-readable docs         │
│  ├── /glama.json            — Glama auto-discovery      │
│  └── Smithery / PulseMCP / mcp.so listings              │
└─────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
studiomcphub.com/
├── CLAUDE.md              # THIS FILE
├── src/
│   ├── mcp_server/        # FastMCP server (Streamable HTTP)
│   │   ├── server.py      # Main MCP server entry point
│   │   └── config.py      # Server configuration
│   ├── tools/             # MCP tool implementations
│   │   ├── generate.py    # SD 3.5 Large image generation
│   │   ├── upscale.py     # ESRGAN upscaling
│   │   ├── enrich.py      # Nova metadata enrichment
│   │   ├── infuse.py      # Atlas metadata infusion
│   │   ├── register.py    # Hash registration (Aegis)
│   │   ├── store.py       # Arweave permanent storage
│   │   ├── mint.py        # NFT minting (Polygon)
│   │   ├── verify.py      # Provenance verification
│   │   └── pipeline.py    # Full pipeline orchestration
│   ├── payment/           # Payment processing
│   │   ├── x402.py        # x402 protocol (USDC/Base)
│   │   ├── stripe_pay.py  # Stripe per-call
│   │   └── gcx_credits.py # GCX token/credit system
│   ├── auth/              # Authentication
│   │   └── oauth.py       # OAuth 2.0 provider
│   └── api/               # REST API endpoints
│       └── routes.py      # Health, pricing, status
├── site/                  # Landing page
│   ├── templates/
│   │   └── index.html     # Main landing page
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
├── tests/                 # Test suite
├── docs/                  # Documentation
├── .well-known/
│   └── mcp.json           # MCP Server Card
├── llms.txt               # LLM-readable documentation
├── glama.json             # Glama auto-discovery
├── smithery.yaml          # Smithery registry config
├── Dockerfile             # Cloud Run deployment
├── requirements.txt       # Python dependencies
├── deploy.sh              # Deployment script
└── firebase.json          # Firebase Hosting config
```

---

## Tool Pricing (Per Call)

| Tool | x402 (USDC) | Stripe (USD) | GCX Credits |
|------|-------------|--------------|-------------|
| generate_image | $0.08 | $0.10 | 10 GCX |
| upscale_image | $0.04 | $0.05 | 5 GCX |
| enrich_metadata | $0.03 | $0.04 | 4 GCX |
| infuse_metadata | $0.01 | $0.02 | 2 GCX |
| register_hash | $0.01 | $0.02 | 2 GCX |
| store_permanent | $0.05 | $0.06 | 6 GCX |
| mint_nft | $0.10 | $0.12 | 12 GCX |
| verify_provenance | FREE | FREE | FREE |
| full_pipeline | $0.25 | $0.30 | 30 GCX |

**GCX Exchange Rate**: $5.00 = 100 GCX (5 cents each, ~17% discount vs Stripe)

---

## Payment Tiers

### Tier 1: Anonymous Agent (x402)
- No account required
- Pay per call with USDC on Base L2
- Wallet address in payment header
- Lowest fees (crypto-native)

### Tier 2: API Key (Stripe)
- Optional account creation
- Stripe payment per call
- API key in Authorization header
- Usage dashboard

### Tier 3: GCX Credit Holder
- Pre-purchase credits ($5 = 100 GCX)
- Account with balance tracking
- Best per-call rate (~17% discount)
- Priority queue access

### Tier 4: Studio Subscriber (Golden Codex)
- Full golden-codex.com SaaS access
- MCP tools included in subscription
- Human UI + agent API
- Custom models, batch processing

---

## Key Commands

```bash
# Development
cd /mnt/c/Users/atmta/source/repos/studiomcphub.com
pip install -r requirements.txt
python -m src.mcp_server.server          # Run MCP server locally

# Testing
pytest tests/ -v

# Deployment
./deploy.sh                              # Deploy to Cloud Run
gcloud run deploy studiomcphub \
  --source . \
  --region us-west1 \
  --project the-golden-codex-1111

# Firebase Hosting (landing page)
npx firebase deploy --only hosting:studiomcphub
```

---

## Competitive Position

| Feature | StudioMCPHub | Other MCP Hubs |
|---------|-------------|----------------|
| Image Generation (SD 3.5L) | Yes | Thin wrappers only |
| ESRGAN Upscaling | Yes | Nobody |
| AI Metadata Enrichment | Yes | Nobody |
| XMP/C2PA Infusion | Yes | Nobody |
| Hash Registration | Yes | Nobody |
| Arweave Storage | Yes | Nobody |
| NFT Minting | Yes | Nobody |
| Full Pipeline | Yes | Nobody |
| x402 Payments | Yes | MCPay (wrapper only) |
| Stripe Payments | Yes | Nobody |
| Credit System | Yes (GCX) | Nobody |

**We are the first creative AI post-production MCP hub.**

---

*Metavolve Labs, Inc. | San Francisco, California*
*"Every agent deserves a studio."*
