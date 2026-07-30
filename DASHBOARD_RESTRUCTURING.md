# Dana Point PULSE — Multi-Page Dashboard Restructuring

**Goal:** Move from "everything on one page" to focused, single-topic pages that match the clean HTML approach. Each page shows one section at a time: metrics + graphs + insights, no clutter.

**Status:** Planning & Implementation Strategy

---

## Problem Statement

Current Streamlit dashboard:
- ❌ 9 tabs (Overview, STR, Forward Outlook, Visitor Economy, Feeder Markets, Event Impact, Supply, Market Intel, Data)
- ❌ Each tab is dense (2-6 sub-tabs, 4-8 charts, 100+ metrics)
- ❌ Ticker shows stale + current data mixed together → confusing
- ❌ Insights buried deep in text → hard to scan
- ✅ Original HTML prototype: clean, focused, one section per page

**Solution:** Restructure into modular pages, each with:
1. **Headline insight** (forward-looking signal)
2. **2-4 hero metrics** (current performance)
3. **1-2 charts** (trend or breakdown)
4. **Actionable recommendations** (1-3 bullet points)
5. **Related pages** (exploration links)

---

## Proposed Page Hierarchy

### Tier 1: Core Operations (Hotel Performance)

| Page | Focus | Chart | Metrics |
|------|-------|-------|---------|
| **① Occupancy Outlook** | Current → Next 30 days | Daily occ trend (7d/30d smoothed) | Occ %, YoY delta, Days >80%, Next week forecast |
| **② Rate Strategy** | ADR & pricing power | ADR trend + comp set benchmark | ADR, ADR YoY, RGI vs. comp set, Weekend premium |
| **③ Revenue Generation** | RevPAR & profitability | RevPAR trend + event impact overlay | RevPAR, RevPAR YoY, TBID potential, TOT potential |
| **④ Compression Calendar** | Quarterly peak planning | Heatmap: occ by week/day for next 2Q | Days >80%, Days >90%, Pricing floor recommendations |

### Tier 2: Visitor Economy (Demand Side)

| Page | Focus | Chart | Metrics |
|------|-------|-------|---------|
| **⑤ Visitor Markets** | Where visitors come from | Top 10 DMAs by visitor days (last 12m) | Total trips, OOS %, Top DMA, Repeat % |
| **⑥ Spend Pathways** | Where $ goes (category breakdown) | Donut: $ by category (dining, retail, etc.) | Total spend, Dining $, Accommodation $, ROAS |
| **⑦ Stay Patterns** | Length of stay distribution | LOS distribution + YoY | Avg LOS, % overnight, Hotel ADR vs. STVR |
| **⑧ Group Demand** | Group booking strategy | Annual group demand vs. transient | Group mix %, Group displacement risk, Optimal season |

### Tier 3: Strategic Planning (Forward-Looking)

| Page | Focus | Chart | Metrics |
|------|-------|-------|---------|
| **⑨ Events Impact** | Events as revenue drivers | Event attendance vs. ADR lift | Event $ impact, attendee count, ADR lift, ROI |
| **⑩ Market Intelligence** | Competitive & external factors | CoStar comp set performance | RGI, market velocity, seasonal trends, risk signals |
| **⑪ Stakeholder Brief** | Role-specific summary | Varies by role (City/Hotels/BID/Fest) | Role-specific KPIs, next best actions |
| **⑫ Brain Status** | Data pipeline health | Pipeline step status, freshness, errors | Last refresh, data age by source, ⚫/🟡/🟢 health |

---

## Page Template Structure

Each page follows this layout:

```
┌─────────────────────────────────────────────────────────┐
│ ⚡ SECTION TITLE (emoji + h1)                           │
│ Forward-looking headline (from insights_daily)          │
└─────────────────────────────────────────────────────────┘

┌──────────────────────────────────┬──────────────────────┐
│  🟢 Occ: 78.5%                   │ 📊 Trips: 2.34M     │
│  ▲ +2.1pp YoY                    │ 📍 OOS: 42%         │
│  Days >80%: 12 this Q            │ 💰 Spend: $18.2M    │
│  Forecast: Moderate (next 30d)   │ ⭐ Repeat: 41%      │
└──────────────────────────────────┴──────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  [Chart 1] — Trend (Occupancy last 12 months)          │
│  [Chart 2] — Breakdown (Top 10 markets by $ spend)     │
└─────────────────────────────────────────────────────────┘

📋 RECOMMENDATIONS
  → Action 1: Launch midweek packages for Sept, ROI: $120K
  → Action 2: Negotiate with top 3 feeder markets
  → Action 3: Monitor comp set; pivot if RGI drops <95

🔗 RELATED PAGES
  [➜ Stay Patterns] [➜ Group Demand] [➜ Market Intel]
```

---

## Navigation Structure

**Redesigned Tab Bar** (Streamlit `st.tabs()` or custom horizontal menu):

```
🏠 OVERVIEW  →  OPERATIONS  →  VISITOR ECONOMY  →  STRATEGY  →  ADMIN
    (Tier 3)     (Tier 1)        (Tier 2)        (Tier 3)      (Data)
```

**Within each tier:** Horizontal "Next Page" buttons at bottom.

Example flow:
- Overview → Occ Outlook → Rate Strategy → Revenue → Compression Calendar
- Then: Visitor Markets → Spend Pathways → Stay Patterns → Group Demand
- Then: Events Impact → Market Intel → Stakeholder Brief
- Finally: Data Vault (pipeline status, table browser)

---

## Implementation Roadmap

### Phase 1: Core Components (This Sprint)
- [x] Data quality checker (`data_quality.py`)
- [x] Redesigned ticker (`ticker_redesign.py`)
- [ ] Update dashboard styles for multi-page layout
- [ ] Create page template utilities

### Phase 2: Tier 1 (Hotel Operations) — 2 weeks
- [ ] Occupancy Outlook page
- [ ] Rate Strategy page
- [ ] Revenue Generation page
- [ ] Compression Calendar page
- [ ] Navigation between Tier 1 pages

### Phase 3: Tier 2 (Visitor Economy) — 2 weeks
- [ ] Visitor Markets page
- [ ] Spend Pathways page
- [ ] Stay Patterns page
- [ ] Group Demand page
- [ ] Cross-tier navigation links

### Phase 4: Tier 3 (Strategic) — 2 weeks
- [ ] Events Impact page
- [ ] Market Intelligence page
- [ ] Stakeholder Brief (role-selector)
- [ ] Brain Status (pipeline health)
- [ ] Full app integration

### Phase 5: Polish & Optimization — 1 week
- [ ] Mobile responsiveness
- [ ] Chart downloads on all pages
- [ ] Performance optimization (caching)
- [ ] QA & testing

---

## Data Quality Integration

Each page includes a **freshness indicator** (top-right):

```
✓ Current (STR as of 2025-07-29)  |  ⚠ 2024 annual data  |  🔄 Forecast (30d out)
```

**Ticker rules** (after data_quality checks):
- **Show in CURRENT section:** STR metrics ≤ 5 days old
- **Show in FORWARD section:** Forecasts & projections
- **Move to REFERENCE:** Historical data, 2024 benchmarks, event metrics
- **Hide:** Data > 30 days old (unless it's historical trend context)

---

## Key Design Principles

1. **One insight per page** — Each page answers ONE question: "How is occupancy?", "Where do visitors come from?", etc.

2. **Scannable in 2 minutes** — No page requires scrolling beyond the fold on desktop.

3. **Current ≠ Historical** — Separate today's metrics from trend context. Historical data is always labeled as reference.

4. **Forward-looking default** — Headline always surfaces the most actionable insight (next 30–90 days).

5. **Mobile-first sub-sections** — Charts stack on mobile; metrics remain side-by-side on desktop.

6. **Every chart is downloadable** — CSV for data export, PNG for presentations.

7. **No "see details elsewhere"** — If a page mentions "see page X," there's a clickable link.

---

## Current vs. Historical Data Handling

### Current (Display Prominently)
- STR daily/monthly ≤ 5 days old → **HERO KPI section**
- Current quarter compression → **FORWARD section**
- Latest social followers → **Context sidebar**

### Historical (Reference Only, Labeled)
- Datafy 2024 annual data → "2024 annual baseline"
- Zartico Jun 2025 snapshot → "Historical growth story (2023–2025)"
- Past event metrics → "Ohana 2025 case study"

### Not Shown (Deep Dive Only)
- Data > 60 days old (unless part of multi-year trend)
- Pre-2023 benchmarks (except for growth narrative)
- Incomplete/errored data states

---

## Ticker Redesign Summary

Three sections replacing old mixed ticker:

| Section | Purpose | Data Age | Example |
|---------|---------|----------|---------|
| **CURRENT** | Today's operations | ≤ 5 days | Occ 78%, ADR $320, RevPAR $251 |
| **FORWARD** | Next 30–90 days | Forecast | Q4 has 22 compression days, book strong |
| **REFERENCE** | Context & benchmarks | 2024 annual or historical | 2.34M annual trips (2024), 41% repeat |

**Visual separation:** Color borders (teal for current, cyan for forward, purple for reference).

---

## Success Metrics

✓ Page load time < 2s
✓ No stale data on first screen
✓ "Top Signal" insight clearly visible & readable
✓ Each page answers its core question without external links
✓ Users can navigate tier 1 → tier 2 → tier 3 without getting lost
✓ Ticker data quality score ≥ 95% (green status indicator)

---

## Migration Path (Non-Breaking)

1. **Week 1:** Add data_quality checks to existing dashboard (no UI changes)
2. **Week 2:** Deploy redesigned ticker alongside old ticker (feature flag)
3. **Week 3–4:** Build Tier 1 pages in a feature branch
4. **Week 5:** Merge & enable new structure (old tabs disabled)
5. **Week 6:** Archive/remove old code

Users see one dashboard; backend validates & improves data quality continuously.

---

## Questions for Review

1. Should "Overview" be a dashboard summary or the first Tier 1 page?
2. Do we need a "Favorites" or "Custom Dashboard" feature for role-specific defaults?
3. Should graphs auto-update (Streamlit polling) or stay static (user-refreshes)?
4. How often should the ticker rotate data (every 5s like 1ax Bloomberg)?
