---
name: studiomcphub-studio
version: 0.1.0
description: "Image to Retail in 90 seconds. 10-stage creative pipeline: background removal, palette extraction, resize, 6-product mockups, CMYK conversion, print-ready PDF, SVG vectorization, invisible watermarking, AI metadata enrichment, ESRGAN upscaling. Local DAM organizes all outputs. HTML preview gallery."
author: Metavolve Labs
homepage: https://studiomcphub.com
tags:
  - creative-ai
  - image-processing
  - print-on-demand
  - dam
  - mockup
  - upscaling
  - metadata
mcp:
  servers:
    - name: studiomcphub
      url: https://studiomcphub.com/mcp
      transport: streamable-http
      description: "32 MCP tools (19 free) for the complete creative AI pipeline"
---

# StudioMCPHub Studio

**Image to Retail in 90 seconds.**

Drop an image, get back: transparent PNG, color palette, product mockups (6 products), CMYK print files, print-ready PDFs with bleed/crop marks, SVG vectors, invisible watermarks, AI-enriched metadata, and 4x ESRGAN upscales. All organized in a local DAM with HTML preview.

## Quick Start

```bash
pip install studiomcphub-studio
studio init my-project && cd my-project
studio process artwork.png -c my-collection
studio preview my-collection
```

## Pipeline Stages

| # | Stage | What it does | Free? |
|---|-------|-------------|-------|
| 1 | remove_bg | Transparent PNG (U2-Net) | Yes |
| 2 | palette | 6-color hex palette | Yes |
| 3 | resize | Fit to max dimensions | Yes |
| 4 | mockup | T-shirt, poster, canvas, phone, mug, tote | Yes |
| 5 | cmyk | CMYK @ 300 DPI for print | Yes |
| 6 | print_ready | PDF with bleed + crop marks | Yes |
| 7 | vectorize | SVG via vtracer | Yes |
| 8 | watermark | Invisible DCT watermark | Yes |
| 9 | enrich | AI metadata (Gemini) | 1-2 GCX |
| 10 | upscale | 4x ESRGAN | 1 GCX |

## Configuration

Edit `studio.json` to customize stages, mockup products, print sizes, and more.

## POD Export (Phase 2)

```bash
studio export my-collection --platform gooten
studio export my-collection --platform printful
studio export my-collection --platform printify
```
