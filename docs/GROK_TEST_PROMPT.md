# StudioMCPHub — Full Deployment Test Prompt for Grok

## Context

You are testing StudioMCPHub, a new MCP (Model Context Protocol) server that offers creative AI tools as paid services for autonomous agents. It was built by an AI (Claude) for AI agents. The site is live and you need to verify every public-facing endpoint, the landing page, discovery files, pricing accuracy, and API behavior.

**Live URLs:**
- Website: https://studiomcphub.web.app
- GitHub: https://github.com/codex-curator/studiomcphub

---

## TEST SUITE

### Phase 1: Discovery & Landing Page

**1.1 — Landing Page Load**
- Visit https://studiomcphub.web.app
- Verify the page loads with a dark monospace aesthetic
- Check that the sticky nav has: Tools, Pipeline, Pricing, GCX Credits, Support, GitHub
- Verify the green "online" status indicator is pulsing in the nav
- Confirm the hero section says "Creative AI tools for autonomous agents" with "built by AI, for AI"
- Count the badges: should be 6 (MCP Server, x402 Payments, First of Its Kind, Streamable HTTP, 9 Tools, NVIDIA L4 GPU)

**1.2 — Terminal Connect Section**
- Verify there are 4 tabs: Claude Code, Cline / VS Code, cURL, Python
- Click each tab and verify the code examples switch correctly
- Confirm the MCP endpoint URL shown is: `https://studiomcphub.com/mcp`
- In the Claude Code tab, verify the JSON shows `"transport": "streamable-http"`
- In the cURL tab, verify it shows the `.well-known/mcp.json` discovery URL

**1.3 — Tools Section**
- Count the tool cards: should be exactly 9
- Verify each card has: icon, name, description, price (GCX + USD), engine name
- Check these specific prices:
  - generate_image: 8 GCX / $0.80, engine: SD 3.5L
  - upscale_image: 2 GCX / $0.20, engine: ESRGAN
  - enrich_metadata: 2 GCX / $0.20, engine: Nova / Gemini
  - infuse_metadata: 1 GCX / $0.10, engine: Atlas / ExifTool
  - register_hash: 1 GCX / $0.10, engine: Aegis
  - store_permanent: 15 GCX / $1.50, engine: Archivus / AR
  - mint_nft: 10 GCX / $1.00, engine: Mintra / Polygon
  - verify_provenance: FREE, engine: Aegis
  - full_pipeline: 5 GCX / $0.50, engine: All Agents
- Verify the full_pipeline card has a subtle purple gradient background
- Hover over cards and check for the top gradient border animation

**1.4 — Pipeline Section**
- Verify 7 stages displayed in order: Generate → Upscale → Enrich → Infuse → Register → Store → Mint
- Each stage should show a number (01-07), name, and engine
- Confirm the description mentions `full_pipeline` and `options.skip`

**1.5 — Payment Methods Section**
- Verify 3 payment cards:
  - x402 / USDC: labeled "For Agents", has teal "FOR AGENTS" badge, 5 features listed
  - Stripe: labeled "Traditional rails", 4 features
  - GCX Credits: labeled "Wallet = Account", mentions $0.10/GCX base and $0.0625 at Studio, 5 features
- The x402 card should have a teal border (recommended)

**1.6 — Loyalty Rewards Section**
- Verify "5% Credit-Back on Every Call" heading in green
- Check that it explains: per wallet, non-transferable, no expiration
- Verify the math examples: 200 GCX → 10 credits → 1 free pipeline
- Confirm it says redeemed calls don't earn credits

**1.7 — GCX Credits Section**
- Verify header shows "1 GCX = $0.10"
- Check 4 GCX packs:
  - Starter: $5 / 50 GCX / $0.10 per
  - Creator: $10 / 100 GCX / $0.10 per
  - Pro: $50 / 600 GCX / $0.083 per / "Save $10"
  - Studio: $100 / 1,600 GCX / $0.0625 per / "Save $60"
- Pro pack should have "Most Popular" label and gold border
- Verify the "What can you do with 100 GCX?" examples
- Confirm "Wallet = Account" explanation at the bottom

**1.8 — Pricing Table**
- Verify table has columns: Tool, Engine, GCX, x402/Stripe, At Studio Rate
- Cross-check all 9 tool rows against the tool cards (prices must match)
- verify_provenance row should show "FREE" across all columns in green
- full_pipeline row should be bold
- Check the footnote explains base rate ($0.10) vs Studio rate ($0.0625)
- Verify volume discount mention: 10% at $50, 20% at $100, 30% at $200

**1.9 — Support Form**
- Verify the support section exists with terminal-style container
- Check the form has: Type dropdown (6 options), Contact field, Subject, Description, Submit button
- Verify the 6 ticket types: Bug Report, Credit/Payment Issue, Feature Request, General Feedback, Copyright/Compliance, Enterprise Inquiry
- Check the agent API hint at the bottom: `POST /api/support/tickets`

**1.10 — Golden Codex CTA**
- Verify the gold-bordered CTA box with "Want the full studio experience?"
- Check two buttons: "Visit Golden Codex Studio" → golden-codex.com, "View Source on GitHub" → github.com/codex-curator/studiomcphub

**1.11 — Footer**
- Verify 6 links: MCP Server Card, llms.txt, Pricing API, Golden Codex, Artiswa, GitHub
- Confirm "Metavolve Labs, Inc. · San Francisco"
- Confirm motto: "Every agent deserves a studio."

---

### Phase 2: Discovery Files

**2.1 — MCP Server Card**
- Fetch https://studiomcphub.web.app/.well-known/mcp.json
- Verify it returns valid JSON with:
  - name: "StudioMCPHub"
  - version: "0.1.0"
  - transport: "streamable-http"
  - endpoint: "https://studiomcphub.com/mcp"
  - 3 authentication schemes (x402, bearer, none)
  - 9 tools with prices matching the landing page
  - payment.x402.wallet: "0xFE141943a93c184606F3060103D975662327063B"
  - payment.x402.chain: "base"
  - links to documentation, pricing, studio, github

**2.2 — LLMs.txt**
- Fetch https://studiomcphub.web.app/llms.txt
- Verify it's plain text, not HTML
- Check it has sections for: MCP Endpoint, Available Tools (9), Payment Methods (3), Human Studio
- Verify each tool has description, input/output, and price
- Confirm wallet address matches: 0xFE141943a93c184606F3060103D975662327063B

**2.3 — Pricing API**
- Fetch https://studiomcphub.web.app/pricing.json
- Verify valid JSON with:
  - pricing_version: "v2"
  - gcx_token.base_rate: 0.10
  - 4 gcx_packs (Starter, Creator, Pro, Studio) with correct GCX amounts
  - 4 subscriptions (free, curator, studio, gallery) with correct monthly GCX
  - 9 tools with gcx and base_usd values
  - 2 combos (creative_pipeline: 14, full_with_mint: 39)
  - 4 volume_discount tiers
  - enterprise_trigger_usd: 200
- Cross-check ALL tool prices against the landing page and mcp.json

---

### Phase 3: Pricing Consistency Audit

This is the most critical test. All prices must be consistent across every surface.

**3.1 — Cross-Surface Price Check**
For each of the 9 tools, verify the GCX cost is IDENTICAL across:
1. Landing page tool cards
2. Landing page pricing table
3. pricing.json API
4. .well-known/mcp.json
5. llms.txt

Expected values:
| Tool | GCX | Base USD |
|------|-----|----------|
| generate_image | 8 | $0.80 |
| upscale_image | 2 | $0.20 |
| enrich_metadata | 2 | $0.20 |
| infuse_metadata | 1 | $0.10 |
| register_hash | 1 | $0.10 |
| store_permanent | 15 | $1.50 |
| mint_nft | 10 | $1.00 |
| verify_provenance | 0 | FREE |
| full_pipeline | 5 | $0.50 |

**3.2 — GCX Pack Math Verification**
- Starter: $5 / 50 GCX = $0.10/GCX (correct)
- Creator: $10 / 100 GCX = $0.10/GCX (correct)
- Pro: $50 / 600 GCX = $0.0833/GCX (17% off $0.10)
- Studio: $100 / 1600 GCX = $0.0625/GCX (38% off $0.10)

**3.3 — Studio Rate Column Check**
Verify the "At Studio Rate" column in the pricing table equals GCX * $0.0625:
- generate_image: 8 * 0.0625 = $0.50
- upscale_image: 2 * 0.0625 = $0.125
- enrich_metadata: 2 * 0.0625 = $0.125
- etc.

**3.4 — Combo Pipeline Math**
- creative_pipeline (14 GCX) = generate(8) + upscale(2) + enrich(2) + infuse(1) + register(1) ✓
- full_with_mint (39 GCX) = creative(14) + store(15) + mint(10) ✓

---

### Phase 4: GitHub Repository Audit

**4.1 — Repo Structure**
- Visit https://github.com/codex-curator/studiomcphub
- Verify it's public
- Check the repo description mentions "Creative AI MCP server"
- Verify the directory structure includes: src/, site/, docs/, tests/, .well-known/
- Count total files (should be 30+)

**4.2 — CLAUDE.md Review**
- Read CLAUDE.md in the repo root
- Verify it documents: architecture, directory structure, all 9 tools, pricing table, payment tiers, GCX exchange rate, competitive position
- Check the competitive position table claims "Nobody" for 10+ features

**4.3 — Source Code Spot Check**
- Read src/mcp_server/config.py — verify PRICING dict matches all published prices
- Read src/tools/__init__.py — verify dispatch_tool handles all 9 tools
- Read src/payment/loyalty.py — verify LOYALTY_RATE = 0.05 (5%)
- Read src/payment/x402.py — verify wallet address matches
- Read Dockerfile — verify it uses gunicorn and exposes port 8080

---

### Phase 5: Responsive & Mobile

**5.1 — Mobile Viewport**
- Test at 375px width (iPhone SE)
- Verify nav collapses (links hidden, brand + status visible)
- Tool grid should be single column
- GCX bundles should stack vertically
- Payment cards should stack vertically
- Pipeline stages should still be readable

**5.2 — Tablet Viewport**
- Test at 768px width
- Tool grid should be 2 columns
- Payment and GCX grids should adjust

---

### Phase 6: Accessibility & SEO

**6.1 — Meta Tags**
- Check page title: "StudioMCPHub — Creative AI Tools for Autonomous Agents"
- Verify Open Graph tags (og:title, og:description, og:type, og:url)
- Check Twitter card meta tag
- Verify canonical URL and robots meta

**6.2 — Semantic Structure**
- Verify proper heading hierarchy (h1, h2 usage)
- Check that all interactive elements are keyboard accessible
- Verify form labels exist for all inputs

---

### Phase 7: Edge Cases & Error States

**7.1 — 404 Handling**
- Visit a non-existent path like /this-does-not-exist
- Should redirect to index.html (SPA rewrite configured in firebase.json)

**7.2 — CORS Headers**
- Check .well-known/mcp.json has Access-Control-Allow-Origin: *
- Check llms.txt has Access-Control-Allow-Origin: *
- Check pricing.json has Access-Control-Allow-Origin: *

---

## Deliverable

After completing all tests, produce a report with:
1. **PASS/FAIL** for each numbered test
2. **Screenshots** of any failures
3. **Pricing consistency matrix** — a table showing the price from each surface for each tool
4. **Recommendations** — anything that should be fixed before production launch
5. **Overall assessment** — is this ready for MCP directory submission (Smithery, Glama, mcp.so)?

---

*Test authored by Claude (Opus 4.6) for Grok — built by AI, tested by AI, for AI.*
*"Every agent deserves a studio."*
