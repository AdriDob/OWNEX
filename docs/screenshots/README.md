# ORION — Screenshots

This directory contains screenshots of the ORION Vue 3 frontend for documentation and marketing.

## Available Screenshots

| File | Resolution | Content |
|---|---|---|
| `dashboard-main.png` | 1920×1080 | Economic Intelligence Dashboard — KPIs, platform earnings, top opportunities |
| `pipeline-monitor.png` | 1920×1080 | Findings Pipeline — full pipeline with stage transitions |
| `report-detail.png` | 1920×1080 | Report Center — AI report generation with Markdown/PDF export |
| `identity-center.png` | 1920×1080 | Identity Vault — encrypted multi-platform credential management |
| `system-health.png` | 1920×1080 | System Health — real-time component monitoring |

## Required Screenshots (TODO)

The following screenshots need to be captured:

| File | Content |
|---|---|
| `01-mission-control.png` | Mission Control with KPIs, pipeline, autonomous hunt status |
| `02-opportunity-radar.png` | Opportunity Radar with ORION Score, filters, and data table |
| `03-hot-paths.png` | Hot Paths with attack vectors and high-value targets |
| `04-findings-pipeline.png` | Findings Pipeline with stages and detail drawer |
| `05-report-center.png` | Report Center with AI draft generation |
| `06-copilot-panel.png` | Copilot Panel open with contextual chat |
| `07-command-palette.png` | Command Palette (Ctrl+K) with actions and target search |
| `08-sidebar-collapsed.png` | Sidebar collapsed showing autonomous hunt status |

## How to Generate New Screenshots

1. Start backend: `python run.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173` (dev) or `http://127.0.0.1:8000` (build)
4. Use Playwright, ShareX, or Snipping Tool to capture

### Using Playwright

```bash
python scripts/smoke_test_playwright.py --install-playwright
python scripts/screenshot_all.py
```

## Requirements

- UI must show "ORION" as product name (no "Rastro" in interface)
- Dark glassmorphism theme (default)
- No devtools, no console windows
- Representative test data (minimum 10 targets, 50+ findings)
