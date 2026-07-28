# Project: VDP Analytics (Visit Dana Point)

DMO tourism analytics platform — ETL pipeline, SQLite brain, Streamlit dashboard, Claude AI Analyst panel.
Owner: John Picou | Org: gloconllc | Repo: VDPDashboard

---

## Data Hierarchy (NEVER violate)

- **Layer 1 — Truth:** STR daily/monthly exports, Datafy event data, TBID assessment docs. These are vetted. Always cite these first.
- **Layer 1 (Current):** Datafy, CoStar, STR are the CURRENT data sources. Always present these as current performance.
- **Layer 1.5 — Historical Reference:** Zartico (Jun 2025 snapshot) is historical reference only. Use for trend comparison and to tell the growth story. NEVER present Zartico as current data.
- **Layer 2 — Context:** FRED hotel pricing index, CA State TOT data, JWA passenger counts, Visit California forecasts.
- **Layer 2.5 — Social Performance:** Later.com social media exports (Instagram, Facebook, TikTok). Current social data. Use for digital/social narrative alongside STR and Datafy. Files in `data/later/IG/`, `data/later/FB/`, `data/later/TikTok/`. Parsed by `load_later_reports.py` into 12 `later_*` tables.
- **Layer 3 — Color:** Media, social sentiment, competitive anecdotes. Never override Layer 1 with Layer 3.

---

## Repository Structure

```
VDP_Dashboard/                      (project root)
├── CLAUDE.md                       ← YOU ARE HERE
├── dashboard/
│   └── app.py                      ← Streamlit entry point (tabs: Overview, Trends, Forward Outlook, Event Impact, Data Log)
├── data/
│   ├── analytics.sqlite            ← Single source-of-truth database (25+ tables)
│   └── datafy/                     ← Normalized CSV intake files, committed to git
├── downloads/                      ← Raw source files: STR exports, Datafy PDFs, GA4 exports (gitignored)
├── scripts/
│   ├── run_pipeline.py             ← Orchestrator: ETL → KPIs → Insights → log
│   ├── load_str_daily_sqlite.py    ← Daily STR → fact_str_metrics
│   ├── load_str_monthly_sqlite.py  ← Monthly STR → fact_str_metrics
│   ├── load_datafy_reports.py      ← Datafy visitor economy → 17 tables
│   ├── compute_kpis.py             ← Refreshes kpi_daily_summary + kpi_compression_quarterly
│   ├── compute_insights.py         ← Generates insights_daily for 4 audiences (runs DAILY)
│   ├── fetch_costar_data.py        ← CoStar market data
│   ├── fetch_external_all.py       ← Layer-2 external data orchestrator
│   ├── fetch_fred_data.py          ← External context pull
│   ├── fetch_ca_tot.py
│   ├── fetch_jwa_stats.py
│   ├── load_later_reports.py       ← Later.com social media (IG/FB/TikTok) → 12 tables (STEP 10, non-fatal)
│   └── init_sqlite_db.py           ← DB initialization
├── logs/
│   └── pipeline.log
├── .claude/
│   └── commands/
│       ├── enhance.md              ← /enhance slash command
│       ├── refresh.md              ← /refresh slash command
│       └── home-button.md          ← /home-button slash command
├── requirements.txt
├── .gitignore
└── venv/                           (excluded from git)
```

---

## SQLite Schema (data/analytics.sqlite)

### Layer 1 — STR & KPI Tables (Truth)

| Table | Purpose |
|---|---|
| `fact_str_metrics` | Long-format STR metrics (source, grain, property_name, market, submarket, as_of_date, metric_name, metric_value, unit) |
| `kpi_daily_summary` | Wide-format daily KPIs (as_of_date, occ_pct, adr, revpar, occ_yoy, adr_yoy, revpar_yoy, is_occ_80, is_occ_90) |
| `kpi_compression_quarterly` | Compression days per quarter (quarter YYYY-Qn, days_above_80_occ, days_above_90_occ) |
| `load_log` | ETL audit trail (source, grain, file_name, rows_inserted, run_at) |

### Layer 1 — Datafy Visitor Economy Tables (Truth)

| Table | Purpose |
|---|---|
| `datafy_overview_kpis` | Annual visitor overview KPIs (total_trips, overnight_pct, out_of_state_vd_pct, avg_los, etc.) |
| `datafy_overview_dma` | Feeder market DMA breakdown (dma, visitor_days_share_pct, spending_share_pct, avg_spend_usd) |
| `datafy_overview_demographics` | Visitor demographics by segment |
| `datafy_overview_category_spending` | Spending by category (accommodation, dining, retail, etc.) |
| `datafy_overview_cluster_visitation` | Visitation by area cluster type |
| `datafy_overview_airports` | Origin airports by passenger share |
| `datafy_attribution_website_kpis` | Website-attributed trips and estimated destination impact |
| `datafy_attribution_website_top_markets` | Website attribution top feeder markets |
| `datafy_attribution_website_dma` | Website attribution DMA breakdown |
| `datafy_attribution_website_channels` | Website attribution by acquisition channel |
| `datafy_attribution_website_clusters` | Website attribution by area cluster |
| `datafy_attribution_website_demographics` | Website attribution visitor demographics |
| `datafy_attribution_media_kpis` | Media campaign: attributable_trips, total_impact_usd, ROAS |
| `datafy_attribution_media_top_markets` | Media attribution top feeder markets |
| `datafy_social_traffic_sources` | GA4 web traffic sources: sessions, engagement |
| `datafy_social_audience_overview` | Website audience KPIs |
| `datafy_social_top_pages` | Top website pages by view count |

### Intelligence Tables (Generated Daily)

| Table | Purpose |
|---|---|
| `insights_daily` | Forward-looking insights for 4 audiences (as_of_date, audience, category, headline, body, metric_basis JSON, priority, horizon_days) |
| `table_relationships` | Cross-table join/derivation map (table_a, table_b, relationship_type, join_key, description) |

### Dedup Rule

`fact_str_metrics` composite key: `(source, grain, property_name, market, as_of_date, metric_name)` — daily and monthly never collide because `grain` differs.

`insights_daily` unique key: `(as_of_date, audience, category)` — one insight per audience/category per pipeline run.

### Metric Names in fact_str_metrics

`supply`, `demand`, `revenue`, `occ`, `adr`, `revpar`

### Units

- `occ` stored as decimal (0.688 = 68.8%). `kpi_daily_summary.occ_pct` stores percentage (68.8).
- `adr`, `revpar`, `revenue` in USD.
- `supply`, `demand` in room-nights.

### Table Relationships Summary

Key relationships documented in `table_relationships`:
- `fact_str_metrics` → `kpi_daily_summary` (derived_from, as_of_date)
- `kpi_daily_summary` → `kpi_compression_quarterly` (derived_from, quarter)
- `fact_str_metrics` → `datafy_overview_kpis` (cross_ref, report_period — same time window)
- `datafy_overview_dma` ↔ `datafy_attribution_website_dma` (cross_ref, dma)
- `kpi_daily_summary` → `insights_daily` (derived_from, as_of_date)
- `datafy_overview_kpis` → `insights_daily` (derived_from, report_period)
- All `datafy_*` sub-tables → their parent KPI table (enriches, report_period)

---

## TBID Assessment Structure

| Nightly Rate | Assessment Rate |
|---|---|
| ≤ $199.99 | 1.0% |
| $200.00 – $399.99 | 1.5% |
| ≥ $400.00 | 2.0% |
| Blended estimate | ~1.25% |

Formula: `TBID Revenue ≈ Room Revenue × 0.0125`
Formula: `TOT Revenue = Room Revenue × 0.10`

---

## Ohana Fest / Datafy Reference Metrics

- Event expenditure: $14.6M
- Destination spend: $18.4M
- ADR lift during event: $139
- Avg accommodation spend/trip: $1,219
- Out-of-state visitors: 68%
- Spend multiplier: 3.2×

---

## Dashboard Architecture (dashboard/app.py)

- **Framework:** Streamlit (wide layout)
- **DB connection:** `sqlite3` with `?mode=ro` (read-only)
- **Caching:** `@st.cache_data(ttl=300)` on all data loaders
- **Tabs (9):** Overview Brain, STR & Pipeline, Forward Outlook, Visitor Economy, Feeder Markets, Event Impact, Supply & Pipeline, Market Intelligence, Data & Downloads
- **AI Analyst panel:** Server-side Claude API call via `ANTHROPIC_API_KEY` env var. Key never exposed in UI.
- **Home button:** Dashboard title "VDP Analytics" in the header is a clickable link that resets to Overview tab.
- **AI system prompt:** Includes full DB schema for all 25+ tables — AI is aware of every table.

### Data Loaders (always use these names)

- `load_str_daily()` — pivots fact_str_metrics long→wide, converts occ decimal→%
- `load_kpi_daily()` — reads kpi_daily_summary
- `load_compression()` — reads kpi_compression_quarterly
- `load_load_log()` — reads load_log for Data Log tab
- `load_insights(audience=None)` — reads insights_daily (optional audience filter)
- `get_table_counts()` — returns row counts for all 23 tracked tables

---

## Pipeline (scripts/run_pipeline.py)

Execution order:

| Step | Script | Fatal? |
|---|---|---|
| 1 | `load_str_daily_sqlite.py` | Yes — abort if missing |
| 2 | `load_str_monthly_sqlite.py` | Yes — abort if missing |
| 3 | `load_datafy_reports.py` | No — log warning, continue |
| 4 | `compute_kpis.py` | Yes — abort if fails |
| 5 | `compute_insights.py` | Yes — runs every pipeline push |
| 16 | `fetch_eia_gas.py` | No — skip-safe; seeds demo data if no EIA_API_KEY |
| 17 | `fetch_tsa_data.py` | No — skip-safe; seeds benchmark data if live fetch fails |

Each step: logged with timestamp + OK/SKIP/WARN/FAIL to `logs/pipeline.log`.
`compute_insights.py` always runs last — it reads all tables and generates today's forward-looking insights.

---

## Insights Engine (scripts/compute_insights.py)

Generates `insights_daily` rows for 4 audiences on every pipeline run:

| Audience | Categories |
|---|---|
| `dmo` | demand_trend, tbid_projection, feeder_market, compression_outlook, event_roi |
| `city` | tot_revenue, infrastructure, visitor_profile, economic_impact |
| `visitor` | best_value, rate_outlook, upcoming_events, booking_timing |
| `resident` | peak_alert, economic_benefit, quiet_windows, annual_impact |
| `cross` | feeder_value_gap, daytrip_conversion, weekday_los_gap, campaign_seasonality, oos_adr_premium, compression_daytrip |

**Cross-Dataset Insights** require BOTH STR and Datafy data to compute — they are invisible in either dataset alone:
- `feeder_value_gap` — STR ADR × Datafy DMA spend efficiency → LA over-indexed on volume, fly markets (SLC, Dallas, NYC) generate 1.3–1.4× more revenue per trip
- `daytrip_conversion` — STR room revenue × Datafy day_trip_pct → 1.44M day trips; 3% conversion = ~$15M incremental room revenue
- `weekday_los_gap` — STR weekday/weekend occ gap × Datafy avg_LOS → 2.0-day stays concentrate revenue on Fri-Sat; LOS extension worth ~$1M/yr
- `campaign_seasonality` — STR compression by quarter × Datafy attribution channels → campaigns may be amplifying peak (Q3=36 days) vs. building shoulder (Q1=4 days)
- `oos_adr_premium` — STR ADR YOY × Datafy out-of-state spend share → OOS visitors nearly 1:1 spend-to-visit but ADR only +6.7% YOY; rate capture gap exists
- `compression_daytrip` — STR compression days × Datafy day_trip_pct → on 80%+ occ days, day trippers add 0.7× more visitors invisible to hotel data

All insights are forward-looking (horizon_days configurable per insight).
One row per audience/category per day (UPSERT on `as_of_date + audience + category`).

---

## Standard Process — Adding New Data (ALWAYS FOLLOW)

Every time new data, a new source, or new logic is added:

```
1. Raw files  →  data/<source_name>/        (CSV, Excel, PDF — committed to git)
2. Loader     →  scripts/load_<source>.py   (parse → analytics.sqlite table)
3. Relations  →  scripts/build_table_relationships.py   (add entries for new tables)
4. Pipeline   →  scripts/run_pipeline.py    (add new step to STEPS list)
5. Run        →  python scripts/run_pipeline.py
   Step 20 (build_relationships) ALWAYS runs last — auto-refreshes all relationships
6. Dashboard  →  dashboard/app.py           (add loader + visualization for new table)
7. Commit     →  git add data/analytics.sqlite data/<source>/ scripts/ dashboard/
               →  git commit -m "Add <source>: N rows → N tables + N relationships"
               →  git push origin main
```

Raw data directories (canonical locations):
```
data/str/             ← STR Excel exports (str_daily.xlsx, str_monthly.xlsx)
data/datafy/          ← Datafy CSV exports (4 subdirs)
data/costar/          ← CoStar PDFs + CSVs
data/Zartico/         ← Zartico PDF reports
data/Visit_California/← Visit California Excel files
data/later/           ← Later.com CSV exports (IG/, FB/, TikTok/)
downloads/            ← Staging area only — move files to data/<source>/ before running pipeline
```

## Commands

```bash
# Local development
source venv/bin/activate
streamlit run dashboard/app.py

# Full refresh (all tables → KPIs → insights → relationships)
python scripts/run_pipeline.py

# Full refresh + latest code from GitHub
git pull origin main && python scripts/run_pipeline.py

# Rebuild ONLY table relationships (after schema change, no new data)
python scripts/build_table_relationships.py

# Deploy — ALWAYS commit directly to main, never create feature branches
git add <specific files> && git commit -m "description" && git push origin main
# Streamlit Cloud auto-redeploys from main branch
```

---

## Code Style

- Python 3.11+, type hints where practical
- Use `pandas` for data shaping, `sqlite3` for DB access
- Logging via `print()` with timestamps for scripts; `st.spinner()` / `st.success()` for dashboard
- Treat `-` in Excel as NULL (use `pd.to_numeric(..., errors='coerce')`)
- No writes from dashboard — all writes via ETL scripts only
- Use `pd.notna()` for null checks before float conversion
- AP style for all user-facing text

---

## Important Rules

- NEVER commit `.env`, `venv/`, or API keys to git
- `data/analytics.sqlite` IS committed intentionally — it contains STR market data (no PII). Commit after every pipeline run that inserts new rows.
- NEVER override Layer 1 data with Layer 2/3 sources
- ALWAYS run `python scripts/run_pipeline.py` after schema changes — step 20 auto-rebuilds all table relationships
- ALWAYS reference this CLAUDE.md before making changes
- ALWAYS add new table relationships to `build_table_relationships.py` when adding new data sources
- Raw data MUST live in `data/<source_name>/` — never parse from `downloads/` permanently
- Dashboard is customer-facing — no API key fields, no debug output
- Admin-only features (API key field, Pipeline Controls) are gated by `st.query_params.get("admin","").lower() == "true"` — append `?admin=true` to URL to access. Never expose to customers.
- The Anthropic API key is set server-side via `ANTHROPIC_API_KEY` env var only
- After every code change, verify the app still runs: `streamlit run dashboard/app.py`
- `compute_insights.py` must run on every pipeline execution — it is the brain's daily self-update

---

## John Picou Writing Style

When drafting any communication (emails, summaries, reports) on behalf of John Picou:

- **Never use em dashes** ("—"). Use a comma, period, or restructure the sentence instead.
- Tone: warm, direct, and professional. Not stiff or corporate.
- Sign-offs: "Sincerely, John Picou / GloCon Solutions LLC"
- AP style for all user-facing text (no Oxford comma, numerals for 10+, etc.)

---

## Self-Improvement Protocol

After every session or error correction:
1. Reflect on what went wrong and why.
2. Abstract and generalize the learning.
3. Append the lesson to the `## Lessons Learned` section below.
4. Keep each lesson to 1–2 lines.

## Lessons Learned

- STR monthly exports use `-` for missing values; always coerce with `pd.to_numeric(..., errors='coerce')` before insertion.
- Shell prompts (zsh) will error if you paste Python code directly — always edit inside files with nano or Claude Code.
- `float(row.metricvalue)` fails on NaN; use `float(row.metricvalue) if pd.notna(row.metricvalue) else None`.
- Streamlit Cloud requires `requirements.txt` at repo root and `Main file path` must match GitHub breadcrumb exactly.
- GitHub auth from Mac: use Personal Access Token (classic) with `repo` scope, or SSH key.
- `insights_daily` uses UPSERT (ON CONFLICT) keyed on `(as_of_date, audience, category)` — safe to run multiple times per day.
- `table_relationships` documents every cross-table join/derivation — update it whenever a new table is added to the schema.
- The AI system prompt must include full DB schema for all tables so Claude can correctly answer cross-table queries.
- Cross-dataset (`cross` audience) insights require BOTH STR and Datafy to be loaded — they silently return empty if either is missing.
- Always prefix cross insights with `HIDDEN SIGNAL/OPPORTUNITY/RISK/GAP` to flag them as non-obvious findings.
- Zartico is historical reference only (Jun 2025 snapshot). NEVER present Zartico as current data. Datafy/CoStar/STR are current sources. Zartico tells the growth story.
- The VDP events calendar is JavaScript-rendered — live scraping requires Playwright. `fetch_vdp_events.py` seeds 10 known major Dana Point events as fallback data.
- All new Zartico tables (`zartico_*`) use `UNIQUE(month_str)` or `UNIQUE(report_date)` for safe UPSERT re-runs.
- `vdp_events` table uses `UNIQUE(event_name, event_date)` — safe to re-run seeding.
- `beautifulsoup4` is required in `requirements.txt` for the events scraper.
- Platform is branded **PULSE** (Performance, Understanding, Leadership, Spending, Economy). Page title, sidebar, and AI system prompt all use "Dana Point PULSE" — this is live, not just a suggestion.
- `visit_ca_airport_traffic` and `visit_ca_intl_arrivals` use column `month` (not `month_num`) — wrong name causes silent exception → empty DataFrame → ⚫ sidebar indicator.
- Data loaders use `try/except: return pd.DataFrame()` — a ⚫ indicator means the loader threw silently. Diagnose by running SQL directly: `python3 -c "import sqlite3,pandas as pd; print(pd.read_sql_query('SELECT * FROM <table> LIMIT 1', sqlite3.connect('data/analytics.sqlite')))"`.
- ALWAYS commit directly to `main` — never create feature branches. User explicitly requires this.
- Raw data MUST go in `data/<source>/` (not `downloads/`). Loaders read from `data/str/`, `data/datafy/`, etc. — downloads/ is a staging area only.
- `build_table_relationships.py` is the LAST step (step 20) in `run_pipeline.py` — it auto-rebuilds ALL 120+ relationships from the RELATIONSHIPS registry. Always add new entries there when adding tables.
- `table_relationships.created_at` is the correct column name (not `updated_at`) — check schema with `PRAGMA table_info(table_relationships)` before writing UPSERT SQL.
- Multi-model AI: `stream_ai_response(prompt, model_key, _ai_keys)` routes to Anthropic/OpenAI/Google/Perplexity. `_ai_keys` is computed in the sidebar; `selected_model` is stored in session_state. Both have module-level defaults before sidebar renders to prevent NameError.
- NEVER use the Write tool on `.env` — it overwrites the file and destroys live API keys. Always Read first; if the file exists, use Edit to add/change only specific lines.
- STR loaders use bulk `executemany()` + a single upfront `SELECT` of all existing keys — never row-by-row `SELECT COUNT` + `INSERT` (2N round-trips). Keep this pattern for all new loaders.
- Negative metric values in STR data are stored as `NULL`, not floored to `0.0`. Flooring silently masks data quality issues and corrupts downstream TBID/TOT projections.
- Dashboard `_logger = logging.getLogger("vdp_dashboard")` is the standard logger. Use `_logger.debug()` in except blocks so silent failures are diagnosable without crashing the UI.
- Cache TTLs are tiered: real-time KPIs = 300s, social/campaign = 1800s, historical (Zartico/VCA) = 3600s. Don't use 300s for everything.
- `OCC_HIGH_THRESHOLD`, `OCC_MED_THRESHOLD`, `OCC_SHOULDER_TARGET` are named constants at the top of app.py — use these instead of hardcoded 0.90/0.80/0.65 magic numbers.
- `requirements.txt` uses upper-bound pins (e.g., `pandas>=2.0.0,<3.0.0`) to prevent breaking changes on fresh installs. Update upper bounds only with deliberate testing.
- `data/str/*.xlsx` is gitignored — raw STR Excel exports are NOT committed; only `data/analytics.sqlite` is the committed truth.
- **Executive summary design rule:** Main tabs should be 2-minute scans, not data dumps. Move detailed analytics to sub-tabs. Headline insight + 4 hero metrics + call-to-action exploration cards (not 12 metric boxes + 8 button banks).
- **KPI consolidation:** Create utility functions for repeated formatting patterns (e.g., `format_hero_kpi_card()`, `format_exec_kpi_banner()`). Reduces duplicate code, makes style updates centralized, eases maintenance.
- **SQL query batching:** Replace N sequential single-row queries with 1 batched query. Example: 3 separate `SELECT ... FROM later_*_profile_growth` queries → `combine_social_followers()` function. Reduces round-trips and improves performance.
- **Sub-tab naming:** Use consistent, self-explanatory names (Scorecard, Board Report, Goals, AI Assistant) not generic ones (Performance, Stories, Analysis). Users shouldn't need to click to understand content.
- **Exploration cards:** Use small cards with icons, titles, and brief descriptions to guide users to related tabs. Improves navigation without cluttering the main tab.
- **App size management:** Watch line counts. If a single file approaches 18K+ lines, begin extracting components. The Overview tab refactor reduced it from 2,180 → 428 lines—same functionality, clearer intent.
- **Top-spacing nuclear fix:** Streamlit's React sets `paddingTop` inline on `.block-container` AFTER stylesheets load, overriding `!important` CSS rules. Defeat it with: (a) `<style>` injected into `<head>` at runtime (post-emotion, wins cascade), (b) `requestAnimationFrame` loop for 5 s forcing inline `setProperty('padding-top','0px','important')`, (c) `MutationObserver` on `document.documentElement` as persistent watchdog. CSS alone is not sufficient.
- **Dark cards on white page:** `_kfm_card` and similar dark-gradient metric cards look jarring on the light theme. Always check card bg color matches the page theme — use `#FFFFFF` + `border-top` accent for light pages, dark gradient only inside dark-bg sections.
- **Overview headline:** Never default to "On Track" — always pull the highest-priority `cross` or `dmo` insight. Leadership opens the Overview tab first; the headline is the first impression.
- **All-audience summaries:** Every summary section (Overview, Board Report, Forward Outlook tabs) must surface all 5 audiences (dmo, city, visitor, resident, cross). Showing only `dmo` is incomplete — city officials, visitors, and residents are separate stakeholders with different needs.
- **Insight body truncation:** 160 chars is too short for actionable context. Use first 2 sentences (up to 280 chars for overview, 320 for audience tabs). Always find the first `. ` after 60 chars to split at a natural sentence boundary.
- **Audience-labeled insight cards:** When showing group/category insights from multiple audiences, always label each card with the audience name and provide audience-specific action guidance (not a generic "review" CTA).
- **Splash "stuck on loading" bug:** The build-time splash (`patch_streamlit_splash.py`) self-removes when the app mounts. Its `ready()` check must NOT measure `#root` height — the app shell (`.stApp`) is `position:absolute; height:100vh`, so it's pulled out of normal flow and `#root` collapses to height 0 forever. Detect content height inside `[data-testid="stMainBlockContainer"]/.block-container` instead. A broken detector makes the splash hang on its 12 s failsafe = "stuck on loading screen." Verified fix clears the splash in ~0.9 s.
- **STR comp set market is Dana Point, NOT Anaheim.** The 6 comp markets in `fact_str_group_metrics` are: Dana Point, Newport Beach, La Jolla, Santa Barbara, Monterey-Carmel, Huntington Beach. Never default to "Anaheim Area" — that is wrong.
- **`DB_PATH` is a `Path`, not a str.** `sqlite3.connect(DB_PATH + "?mode=ro", ...)` raises `TypeError` (Path + str), which the loader's `except` swallows → silent empty DataFrame → ⚫ indicator. Always read through the cached `get_connection()`; never build a `?mode=ro` URI by concatenating to `DB_PATH`. This bug silently broke load_stvr_summary / load_bts_routes / load_socal_gas / load_weather_forecast / comp-set radar / content funnel.
- **One cached connection, tuned once.** All dashboard reads go through `get_connection()` (`@st.cache_resource`). It applies read PRAGMAs (WAL, synchronous=NORMAL, temp_store=MEMORY, 16MB cache, 128MB mmap, busy_timeout) via `_apply_read_pragmas()`. Never open ad-hoc `sqlite3.connect()` in a loader and never `.close()` the shared connection.
- **Hot-path indexes are embedded in two places** so they exist "all the time": `_init_db()` (CREATE INDEX IF NOT EXISTS — covers fresh Streamlit Cloud DBs) and `scripts/optimize_db.py` (pipeline step: ANALYZE + WAL checkpoint after every refresh). Key index `idx_str_src_grain_date` on `fact_str_metrics(source, grain, as_of_date)` backs the most frequent filter AND satisfies the ORDER BY.
- **Pipeline parallelizes independent fetches.** `run_pipeline.py` runs contiguous runs of `PARALLEL_SAFE` network-bound steps in a thread pool (`PIPELINE_MAX_WORKERS`, default 5). Core STR/KPI/insight steps and anything reading other freshly-written tables stay strictly sequential. `log()` is lock-guarded for thread safety.
- **NEVER `conn.close()` a `get_connection()` handle — it took production down.** `get_connection()` returns a shared `@st.cache_resource` connection reused across every Streamlit rerun. `load_str_compset` / `load_str_holiday_calendar` / `load_str_property_roster` each called `conn.close()`, so the next rerun's `load_str_daily()` crashed with `sqlite3.ProgrammingError: Cannot operate on a closed database` (whole app stuck on loading). Fix: removed the closes; `get_connection()` is now self-healing — `_open_connection()` is the cached builder, `get_connection()` runs `SELECT 1` and rebuilds via `_open_connection.clear()` if the handle was closed. A `with get_connection() as conn:` is fine (sqlite `__exit__` commits, does not close), but a bare `.close()` is poison.
- **`.streamlit/config.toml` is part of the theme, not just server config.** It declared `base="dark"` + `textColor="#F4FAFF"` long after the app moved to a white page. Custom CSS forced the surfaces light but never overrode Streamlit's generated text color, so anything the CSS didn't explicitly recolor rendered near-white on white: inactive tab labels measured **1.05:1** contrast (invisible). If the page is light, the config must say `base="light"`.
- **Measure contrast, don't eyeball it.** Drive the running app with Playwright and compute ratios from `getComputedStyle` against the composited background. That is how the 1.05:1 tab bug was found, and it is how you confirm a fix (now 10.35:1).
- **Careful: `backgroundColor` is empty for gradient backgrounds.** A naive "walk up to the first non-transparent ancestor bg" contrast audit reports the dark app shell behind a light gradient card and floods you with false positives. Verify suspicious hits against a screenshot before "fixing" them.
- **Brand teal `#0891B2` is only 3.68:1 on white** — fine for a chart mark (3:1 floor), too low for text. Use `#0E7490` (5.36:1) for teal text like active tab labels.
- **One chart theme: `dashboard/chart_theme.py`.** `app.py`, `components_group.py`, and `components_coastal.py` each used to carry their own. Import `style_fig` from there; never add a fourth. `style_fig(fig)` with no height now PRESERVES a height the figure already set, so applying it at render time will not resize gauges or tall heatmaps.
- **A categorical palette is validated, not chosen.** Check lightness band, chroma floor, adjacent-pair CVD separation, normal-vision floor, and 3:1 contrast. Order is fixed because checks run on ADJACENT pairs: reordering can silently break CVD. Red is reserved for status and is not a series color. The old Group palette had 6 of 8 colors under 3:1 on white (gold 1.72:1, seafoam 1.48:1) — that was the "washed out" look.
- **Charts can bypass the theme silently.** Grep for `st.plotly_chart(` call sites where the figure never passed through `style_fig` — 42 were found this way. A chart that renders is not a chart that is themed.
- **Freshness checks must anchor to the data, not the calendar.** `audit_app.py` averaged KPIs over the last 90 *calendar* days; whenever STR was behind, the window was empty, `AVG()` returned NULL, and it reported 3 false "out of range" errors. Anchor to `MAX(as_of_date)` and report "no rows" as its own condition.
- **A loader with no chart is invisible work.** `load_weather_forecast()` existed for weeks with zero call sites. After adding a table, check that something actually renders it.

---

## New Tables (2026-03-17)

### Zartico Historical Reference Tables (8 tables)
| Table | Rows | Purpose |
|---|---|---|
| `zartico_kpis` | 4 | Visitor economy KPIs (devices %, spend %, demographics, accommodation %) |
| `zartico_markets` | 11 | Top visitor origin markets (rank, %, avg spend) |
| `zartico_spending_monthly` | 11 | Monthly avg visitor spend vs benchmark (Jul 2024–May 2025) |
| `zartico_lodging_kpis` | 1 | Hotel/STVR summary (YTD occ, ADR, LOS, ADR by day of week) |
| `zartico_overnight_trend` | 13 | Monthly overnight visitor % trend (May 2024–May 2025) |
| `zartico_event_impact` | 1 | Event period vs baseline spend changes |
| `zartico_movement_monthly` | 10 | Visitor-to-resident ratio by month |
| `zartico_future_events_summary` | 1 | YoY event + attendee growth |

### VDP Events Table
| Table | Rows | Purpose |
|---|---|---|
| `vdp_events` | 10 | Known major Dana Point events (scraped or seeded; `is_major` flag) |

---

## Update Log

| Date | Change | Author |
|---|---|---|
| 2026-03-09 | Initial CLAUDE.md created | Claude + John Picou |
| 2026-03-09 | CLAUDE.md installed at project root; slash commands created; home button added to dashboard title | Claude + John Picou |
| 2026-03-16 | Full brain upgrade: insights_daily + table_relationships schema; compute_insights.py (4 audiences, 17 insight types); pipeline updated to run all 25+ tables; Forward Outlook tab added to dashboard; AI system prompt extended with full schema | Claude + John Picou |
| 2026-03-17 | Zartico integration (8 tables, historical reference); VDP Events table (10 seeded events); CoStar filter fix; Data & Downloads dynamic row counts; Zartico section in Visitor Economy tab; 6-point Board Report; pipeline steps 7+8 added | Claude + John Picou |
| 2026-03-17 | Rebrand to Dana Point PULSE; 9-tab layout (+ Feeder Markets, Event Impact, Supply & Pipeline); Visit California ⚫ bug fix; admin mode (?admin=true); PULSE Score widget; footer with GloCon branding + glossary; direct-to-main commit workflow | Claude + John Picou |
| 2026-03-25 | Later.com social media integration (IG/FB/TikTok → 12 tables); Pipeline step 10; Pipeline Status dot; Data & Downloads card; Datafy GA4 summary in Board Report; Performance Command Center card+chart pairs; PULSE Score whitespace fix + scale readability; STR chart animations; Key Forward Metrics date references | Claude + John Picou |
| 2026-04-22 | Full /enhance audit: 53 bare except blocks → logged; SQLite timeout=10; bulk executemany() in STR loaders (2N→1 round-trip); tiered cache TTLs (300/1800/3600s); negative value preservation; NaT date validation; retry logic in FRED/EIA fetch scripts; model selector shows strengths; empty-state card for insights; RevPAR axis label; requirements.txt version pinned; .gitignore xlsx; OCC threshold constants; 8 new lessons learned | Claude + John Picou |
| 2026-03-30 | EIA gas prices + TSA checkpoint data sources (pipeline steps 16+17); intel panels added to tab_sp and tab_dl; gas price correlation section in Market Intelligence; EIA/TSA source health cards in Data Vault; updated DB inventory; EIA/TSA sidebar status dots | Claude + John Picou |
| 2026-03-31 | Multi-model AI engine (Claude + GPT-4o + Gemini + Perplexity Sonar — 8 models); universal stream_ai_response() router; sidebar model selector; Live Market Intelligence panel; all charts downloadable (scale=3, 1600×800); 7 new CSV download buttons; style_fig v4 | Claude + John Picou |
| 2026-03-31 | Data organization standard: all raw data in data/<source>/ canonical dirs; STR files moved to data/str/; build_table_relationships.py (step 20, always-last); 120 relationships (from 37); FRED_API_KEY placeholder; Standard Process section in CLAUDE.md | Claude + John Picou |
| 2026-04-24 | Major Overview tab redesign: reduced from 2,180 to 428 lines; new exec summary format (headline insight + 4 hero metrics + 5 exploration cards); moved AI Analyst panel to dedicated 🤖 AI Assistant sub-tab; consolidated KPI formatting functions into utils.py module; renamed sub-tabs (Scorecard, Board Report, Goals, AI Assistant) for clarity; added error logging to all except blocks; optimized social followers query; created dashboard/assets/styles.css for future stylesheet separation | Claude |
| 2026-04-24 | Full UX/visual audit & enhancement: ticker readability improvement (65%→95% opacity, font 12px→16px, labels 8.5px→9.5px); new format_insight_card() utility for styled metric cards (replaces plain text paragraphs with visual hierarchy); light theme color consistency pass (updated CSS token usage); improved section spacing and visual separation between topic areas | Claude |
| 2026-05-26 | Thursday demo prep: pipeline refresh (28 steps, 29 fresh insights, 288 relationships); top white-space nuclear fix (RAF loop + head-injected style + MutationObserver); hero banner margin-top 0; splash text to pure white; tab bar to clean white-pill SaaS style; Overview exec brief upgraded (live KPI snapshot + status badge + top insight block); Forward Outlook _kfm_card to light theme; font antialiasing global; hero "Brain refreshed" badge | Claude |
| 2026-05-29 | Group & Travel Intelligence tab (PR #35): new 10th tab with 4 sub-tabs (Group Strategy, Traveler Types, National Context, AI Analyst); 5 new charts (TBID bar, occ heatmap, segment donut, revenue funnel, traveler type radar); board-ready executive brief; 2 new cross insights (group_event_synergy, traveler_mix_revenue_gap); 37 total insights; group KPIs in ticker; x-axis readability fix (12px, -30°); insight body text 9.5pt→11.5pt | Claude |
| 2026-05-29 | Summary & audience enhance: 5-audience Stakeholder Intelligence Brief on Overview hero (dmo/city/visitor/resident/cross); Board Report expanded to show all 5 audiences; Forward Outlook audience tabs each get executive summary card; Group Strategy insights labeled by audience with tailored action guidance; insight body expanded from 160→280 chars in overview | Claude |
| 2026-06-16 | Load + refresh speed pass: all dashboard reads routed through one cached, PRAGMA-tuned `get_connection()` (WAL, NORMAL sync, MEMORY temp, 16MB cache, 128MB mmap, busy_timeout); fixed 6 silently-broken loaders (`DB_PATH + "?mode=ro"` TypeError → empty data); hot-path indexes embedded in `_init_db()` + new always-on `scripts/optimize_db.py` pipeline step (indexes + ANALYZE + WAL checkpoint); `run_pipeline.py` now runs independent network fetches in parallel (thread pool, `PIPELINE_MAX_WORKERS` default 5) with lock-guarded logging | Claude |
| 2026-07-27 | Full refresh + readability pass: pipeline rerun (insights for all 5 audiences, relationships 329 → 344 incl. 15 new weather entries, zero orphan tables); **fixed white-on-white text app-wide** by correcting `.streamlit/config.toml` from dark to light theme (inactive tab labels 1.05:1 → 10.35:1); active tab teal → `#0E7490` for 5.36:1; new `dashboard/chart_theme.py` replaces 3 divergent themes and ships a validated palette (old Group palette had 6/8 colors under 3:1); 42 unthemed charts routed through `style_fig`; 2 new visualizations (Visitor Conditions Outlook, Brain Map); `audit_app.py` KPI window anchored to latest data | Claude |
