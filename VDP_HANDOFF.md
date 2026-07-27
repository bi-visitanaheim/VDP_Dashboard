# VDP Dashboard — Handoff Briefing

**Repo:** `gloconllc/vdp_dashboard` · **Product:** Dana Point PULSE · **Owner:** John Picou / GloCon Solutions LLC
**Briefing generated:** 2026-07-27 · **Branch read:** `claude/dashboard-handoff-briefing-gkqbuw`
**No code was changed to produce this document.**

---

## ⚠️ Read this before anything else

**1. The briefing prompt assumed a JavaScript project. This is not one.**
There is no `package.json`, no React, no npm build, no bundler. This is a **Python + Streamlit** app reading a
committed SQLite file. Every section below has been mapped onto the real stack; where a requested concept has no
equivalent (e.g. "build tool", "state management library"), that is stated rather than invented.

**2. There is a live credential leak committed to git.**
A file literally named `.env\r` (trailing carriage return, which is why `.gitignore`'s `.env` rule does not match it)
is **tracked in the repository** and contains `STR_USERNAME` and `STR_PASSWORD` — the STR portal login used by
`scripts/fetch_str_dropbox.py` / `str_playwright_automation.py`. The values are deliberately **not reproduced in this
document.** This should be treated as a real incident: rotate the STR credentials, `git rm --cached` the file, and
assume the secret is compromised in history. See §7.

**3. Section 8 (full source paste) has been deliberately skipped.**
`dashboard/app.py` is **19,181 lines / 1.1 MB**, plus `components_group.py` at 2,312 lines. Pasting these would produce
a multi-megabyte document that no reader or model could usefully consume. Per your instruction, §8 instead gives a
**line-indexed map** of where everything lives so you can request exact ranges. Ask for any range and it can be pulled
verbatim.

**Convention used throughout:** anything marked **[INFERRED]** is my reading of intent, not something the code states.
Everything else is read directly from the source, the schema, or the database.

---

## 1. Stack

There is no `package.json`. Versions below are the **declared constraints** from `requirements.txt` (the project pins
upper bounds rather than exact versions, so installed versions vary by environment). There is no lockfile.

### Core runtime

| Concern | Technology | Declared version |
|---|---|---|
| Language | Python | 3.11+ (per `CLAUDE.md`; `Dockerfile` and CI pin the actual runtime) |
| App framework | **Streamlit** | `>=1.40.0,<2.0.0` |
| Data shaping | **pandas** | `>=2.0.0,<3.0.0` |
| Numerics | **numpy** | `>=1.26.0,<3.0.0` |
| Charting | **Plotly** (`plotly.graph_objects`, `plotly.subplots.make_subplots`) | `>=5.24.0,<6.0.0` |
| Database | **SQLite** (`sqlite3` stdlib) — single file `data/analytics.sqlite`, **committed to git** | stdlib |
| Config/secrets | **python-dotenv** | `>=1.0.0,<2.0.0` |
| Auth (dormant) | streamlit-authenticator | `>=0.3.3,<1.0.0` |

### AI providers (multi-model AI Analyst)

| SDK | Declared version | Used for |
|---|---|---|
| `anthropic` | `>=0.84.0,<1.0.0` | Claude Sonnet 4.6 / Opus 4.6 (default) |
| `openai` | `>=1.30.0,<2.0.0` | GPT-4o, o3-mini — **also reused as the Perplexity client** via `base_url` override |
| `google-generativeai` | `>=0.8.0,<1.0.0` | Gemini 2.0 Flash, Gemini 1.5 Pro |

All three are imported inside `try/except ImportError` with `*_AVAILABLE` flags (`app.py:124–140`), so a missing SDK
degrades rather than crashes.

### ETL / ingestion dependencies

`openpyxl` (`>=3.1.0,<4.0.0`, STR Excel), `xlrd` (unpinned — **the only unpinned dependency**), `pdfplumber`
(`>=0.11.0,<1.0.0`, CoStar/Zartico PDFs), `beautifulsoup4` (`>=4.12.0,<5.0.0`), `requests` (`>=2.31.0,<3.0.0`),
`playwright` (`>=1.40.0,<2.0.0`, headless STR portal download), `pytrends` (`>=4.9.2,<5.0.0`, Google Trends),
`google-auth` / `google-auth-httplib2` / `google-api-python-client` (Drive sync).

### Testing

`pytest` (`>=8.0.0,<9.0.0`), `pytest-cov` (`>=5.0.0,<6.0.0`). Config in `pytest.ini`: `testpaths = tests`,
`addopts = -v --tb=short`. Four test files exist (see §2) — this is a smoke-level suite, not broad coverage.

### Build tool / styling / state management — the honest answers

- **Build tool:** none. Streamlit serves Python directly. Deployment is `streamlit run dashboard/app.py`.
  Deploy targets present in the repo: `Dockerfile`, `railway.toml`, `.devcontainer/`, and Streamlit Cloud
  (per `CLAUDE.md`). Two GitHub Actions workflows: `.github/workflows/pipeline.yml`, `.github/workflows/tests.yml`.
- **Styling:** hand-written CSS injected as strings via `st.markdown(..., unsafe_allow_html=True)`. **17 separate
  `<style>` blocks** inside `app.py`, plus **443 `unsafe_allow_html=True` call sites**. No preprocessor, no CSS
  framework, no utility classes. See §6 — this is the least healthy part of the codebase.
- **State management:** Streamlit's built-in `st.session_state` plus `st.query_params` for deep-linking
  (`?admin=true`, tab index). Caching is the de-facto state layer: `@st.cache_data(ttl=…)` on ~90 loaders and
  `@st.cache_resource` on the single shared DB connection.
- **Date utilities:** stdlib `datetime`/`timedelta` and `pandas.to_datetime` only. No `arrow`, `pendulum`, or similar.
  Date arithmetic for year-over-year is done in **SQLite** (`date(as_of_date, '-1 year')`) — see §5.

---

## 2. File map

Dashboard source and its direct support only. Excluded: `data/` payloads, `logs/`, `.git/`, and the junk
directories described at the end of this section.

```
VDP_Dashboard/
├── CLAUDE.md                          Project memory: data hierarchy, schema, house style, lessons learned (33 KB)
├── requirements.txt                   Dependency constraints (no lockfile)
├── pytest.ini                         pytest config
├── Dockerfile · railway.toml          Container + Railway deploy config
├── .streamlit/config.toml             Streamlit server/theme config (committed; secrets.toml is gitignored)
│
├── dashboard/
│   ├── app.py                     ◀── ENTRY POINT — 19,181 lines. Page config, all CSS, DB layer, ~90 data
│   │                                  loaders, AI router, ~40 chart/card builders, and all 6 tab bodies inline.
│   ├── utils.py                       569 lines. Pure formatting + safe-query helpers. No Streamlit writes.
│   ├── components.py                  709 lines. Self-contained HTML/JS widgets rendered via components.html().
│   ├── components_coastal.py          339 lines. Coastal Intelligence section (beach water quality, whales).
│   ├── components_group.py          2,312 lines. Entire Group & Travel Intelligence tab + its 20 charts.
│   ├── __init__.py                    Empty.
│   ├── assets/styles.css              558 lines — DEAD. Never loaded by app.py. Dark-theme tokens.
│   ├── assets/styles-light.css        284 lines — DEAD. Never loaded by app.py.
│   ├── static/favicon.png             Favicon.
│   ├── app.py.save                    192 KB — DEAD. Stale editor backup, committed to git.
│   └── vdp-dashboard-v2.html           68 KB — DEAD. Standalone HTML prototype, unreferenced.
│
├── scripts/                           ~70 ETL / fetch / maintenance scripts. Highlights:
│   ├── run_pipeline.py            ◀── ORCHESTRATOR. 49-step STEPS list; PARALLEL_SAFE steps run in a thread pool.
│   ├── load_str_daily_sqlite.py       STR daily Excel → fact_str_metrics (fatal on failure)
│   ├── load_str_monthly_sqlite.py     STR monthly Excel → fact_str_metrics (fatal on failure)
│   ├── load_str_multiseg.py           STR segment data → fact_str_group_metrics
│   ├── compute_kpis.py                fact_str_metrics → kpi_daily_summary + kpi_compression_quarterly (fatal)
│   ├── compute_insights.py            All tables → insights_daily, 5 audiences (fatal; runs every pipeline)
│   ├── build_table_relationships.py   Rebuilds table_relationships (step 20 / always last)
│   ├── optimize_db.py                 Hot-path indexes + ANALYZE + WAL checkpoint
│   ├── load_datafy_reports.py         Datafy CSVs → 30+ datafy_* tables
│   ├── load_costar_reports.py         CoStar PDFs/CSVs → costar_* tables
│   ├── load_zartico_reports.py        Zartico PDFs → zartico_* tables (HISTORICAL reference only)
│   ├── load_later_reports.py          Later.com IG/FB/TikTok CSVs → 14 later_* tables
│   ├── load_us_travel_reports.py      U.S. Travel Association benchmarks
│   ├── load_visit_ca*.py              Visit California forecasts / lodging / global market profiles
│   ├── fetch_*.py  (~30 files)        Layer-2 external context: FRED, EIA, TSA, BLS, NOAA, Census, AirNow,
│   │                                  Ticketmaster, Wikipedia, Google Trends, surf, tides, gas, BTS, Airbnb
│   ├── fetch_str_dropbox.py           STR portal auto-download (uses the leaked STR_USERNAME/PASSWORD)
│   ├── str_playwright_automation.py   Headless STR portal driver
│   ├── seed_group_benchmarks.py       Seeds group_intelligence benchmark row
│   ├── compute_strategy_progress.py   Auto-updates strategy_goals.current_value
│   ├── audit_data.py · audit_app.py   Post-run sanity checks
│   ├── patch_streamlit_splash.py      Injects the build-time loading splash
│   ├── send_alerts.py · send_weekly_digest.py   Notification jobs
│   ├── load_str_monthly_sqlite_broken.py        DEAD — named "broken", still committed
│   ├── load_str_monthly_sqlite.py.save          DEAD — editor backup
│   ├── load_str_monthly_sqlite.pyo               DEAD — stale bytecode
│   └── "load_str_monthly_sqlite.py\x18"          DEAD — filename contains a control character (0x18)
│
├── tests/
│   ├── conftest.py · helpers.py       Fixtures + shared helpers
│   ├── test_compute_kpis.py           KPI SQL correctness
│   ├── test_connection_safety.py      Guards the "never .close() the shared connection" rule (see §7)
│   ├── test_dashboard_utils.py        utils.py formatting helpers
│   └── test_str_loaders.py            STR loader dedup/coercion
│
├── data/
│   ├── analytics.sqlite               7.9 MB · 120 tables · COMMITTED INTENTIONALLY (market data, no PII)
│   ├── str/ datafy/ costar/ Zartico/ later/ us_travel/ Visit_California/ bts/ inside_airbnb/ design/
│   └──   (data/str/*.xlsx is gitignored; everything else is committed raw)
│
└── .claude/commands/                  Slash commands: enhance, refresh, demo-prep, home-button, main-task
```

### Junk committed to the repository root

Six directories — **`already/`, `created/`, `if/`, `not/`, `skip/`, `you/`** — plus one named **`#`** are complete
Python 3.9 virtualenvs (`bin/`, `lib/python3.9/site-packages/`, `pyvenv.cfg`), **all tracked in git**. They account
for the bulk of the repo's **4,322 tracked files**.

**[INFERRED]** These were created by a shell command where a sentence was passed to `python -m venv` — the directory
names read as fragments of English prose ("skip … if … not … already … created … you"). They are pure accident and
safe to delete. Also at root: `GlobalMktProfile_UnitedStates (1).zip` (1 MB, committed), and two throwaway repair
scripts `diagnose_docstring.py` / `fix_docstring.py`.

---

## 3. Component inventory

There are no components in the React sense. The equivalents are three layers:

1. **HTML-string builders** — pure functions returning HTML, passed to `st.markdown(..., unsafe_allow_html=True)`.
2. **Figure builders** — functions returning a `plotly.graph_objects.Figure`.
3. **Section renderers** — functions that call `st.*` directly and return `None`.

### 3a. `dashboard/utils.py` — shared formatting layer (imported by `app.py`)

| Function | Renders | Signature |
|---|---|---|
| `format_hero_kpi_card` | Large hero KPI card w/ delta | `(label, value, delta="", delta_class="neutral", color="#00D4C8") -> str` |
| `format_exec_kpi_banner` | Compact exec banner tile | `(label, value, sub="", color="#00D4C8") -> str` |
| `format_section_header` | Icon + title + subtitle header | `(icon, title, subtitle="") -> str` |
| `format_metric_card` | Small metric card | `(label, value, icon="", context="") -> str` |
| `format_insight_card` | Styled insight card w/ accent | `(icon, title, main_value, subtitle="", body="", accent_color="#0284C7") -> str` |
| `format_stat_band` | Horizontal stat band | `(...)` — 130-line builder, largest in the module |
| `format_benchmark_band` | Benchmark comparison band | `(category, icon, color, rows, *, ...) -> str` |
| `format_metric_delta` | Delta value + CSS class | `(value, decimals=1, as_percentage=True) -> tuple` |
| `auto_distribution_analysis` | Auto prose for a distribution | `(labels, values, *, title, noun="share", ...)` |
| `safe_sql_query` | Query → DataFrame, empty on error | `(conn, query, params=()) -> pd.DataFrame` |
| `combine_social_followers` | **1 batched query** replacing 3 per-platform queries | `(conn) -> Dict[str, int]` |
| `safe_execute_with_logging` | try/except wrapper w/ logging | `(func, *args, **kwargs) -> Any` |
| `_stat_band_colors` / `_fmt_val` | Private helpers | — |

**Default color `#00D4C8` in `format_hero_kpi_card` / `format_exec_kpi_banner` is a dark-theme token.** The live app
runs the **light** theme where teal is `#0891B2`. Any call site that omits `color=` renders an off-palette cyan.
See §6.

### 3b. `dashboard/components.py` — embedded HTML/JS widgets

Rendered through `streamlit.components.v1.html()` in sandboxed iframes (their CSS is isolated from the page).

| Function | Renders | Signature | Used at |
|---|---|---|---|
| `inject_shader_wallpaper` | Animated background shader | `() -> None` | `app.py:157` ✅ |
| `render_narrative_box` | Editable narrative `<textarea>` | `(tab_id, sample_text, height=400) -> None` | `app.py:12785`, `15693` ✅ |
| `render_kpi_blob_loaders` | Animated blob loaders | `(height=560) -> None` | **never called** ⚠️ |
| `render_mono_cards` | Monospace card grid | `(cards_data, tab_id, height=280) -> None` | **never called** ⚠️ |
| `render_fun_facts_sprite` | Sprite-animated fun facts | `(facts, height=480) -> None` | **never called** ⚠️ |
| `render_monthly_highlights` | Sliding highlights strip | `(insights, height=260) -> None` | **never called** ⚠️ |
| `render_topic_animation` | Topic animation panel | `(topic, data_points, height=420) -> None` | **never called** ⚠️ |

**5 of 7 are imported at `app.py:41–43` but never invoked** — dead imports of ~450 lines of live code. **[INFERRED]**
these were built for a design pass that was reverted; the imports were left behind.

### 3c. `dashboard/components_coastal.py` — Coastal Intelligence

| Function | Renders | Signature |
|---|---|---|
| `render_coastal_intelligence` | **Public entry.** Composes the three sections below | `(df_kpi) -> None` |
| `render_beach_intelligence` | Beach water-quality panel + chart | `(df_beach, df_kpi) -> None` |
| `render_whale_watching` | Whale-activity panel + chart | `(df_whale, df_kpi) -> None` |
| `render_revenue_opportunities` | Derived revenue-opportunity cards | `(df_kpi, df_beach, df_whale) -> None` |
| `load_beach_water_quality` / `load_whale_watching` | Local loaders | `() -> pd.DataFrame` |
| `sec_div` / `style_fig` | **DUPLICATED** from `app.py` | `(title) -> str` / `(fig, height=400)` |

⚠️ **Duplication:** `sec_div` and `style_fig` exist in both `app.py` (lines 7094, 6942) and `components_coastal.py`
(lines 30, 34) with **different defaults** — `style_fig` defaults to `height=360` in `app.py` and `height=400` in
`components_coastal.py`. Charts in the coastal section are therefore 40px taller than the rest of the app, and a
change to the app-level styling does not propagate to coastal charts.

Called once, at `app.py:18551`.

### 3d. `dashboard/components_group.py` — Group & Travel Intelligence (2,312 lines)

Public entry: `render_group_tab(ai_keys: dict | None = None, selected_model: str = "claude") -> None`, called at
`app.py:18562`. Note the default `selected_model="claude"` is **not a key in `AI_MODELS`** (valid keys are
`claude-sonnet-4-6`, `claude-opus-4-6`, `gpt-4o`, `o3-mini`, `gemini-2.0-flash`, `gemini-1.5-pro`, `sonar-pro`,
`sonar`) — see §7.

*Cached loaders* (`@st.cache_data`, TTL constants `CACHE_TTL_GROUP` / `CACHE_TTL_NATIONAL`):
`_load_group_intel`, `_load_str_group_metrics`, `_load_monthly_occ`, `_load_ust_segments`, `_load_ust_biz`,
`_load_traveler_types`, `_load_group_insights`, `_load_social_summary`, `_load_costar_chain`,
`_load_competitive_set`, `_load_supply_pipeline`, `_load_attribution_groups`, `_load_costar_monthly`.

*Chart builders* (all `-> go.Figure`): `_chart_tbid_bar`, `_chart_occ_heatmap`, `_chart_segment_donut`,
`_chart_revenue_funnel`, `_chart_traveler_radar`, `_chart_competitive_scatter`, `_chart_tbid_chain_waterfall`,
`_chart_supply_pipeline`, `_chart_attribution_channel`, `_chart_costar_occ_overlay`,
`_chart_group_vs_transient_trends`, `_chart_segment_mix_donut`, `_chart_group_adr_premium`,
`_chart_group_event_correlation`, `_chart_property_group_performance`, `_chart_segment_occupancy_heatmap`.

*Card/section helpers:* `_dark_fig(height=320)`, `_metric_box(label, value, note="", color="#0891B2", ...)`,
`_action_card(icon, headline, body, action, ...)`, `_render_shoulder_alignment`, `_render_group_strategy`,
`_render_traveler_types`, `_render_national_context`, `_render_ai_analyst`.

⚠️ `_dark_fig` builds **dark-background** figures inside a **light-theme** page. `CLAUDE.md`'s own lessons flag this
exact anti-pattern ("Dark cards on white page … look jarring"). Unresolved here.

### 3e. `dashboard/app.py` — in-file builders (~40)

*Text/HTML:* `md_to_html`, `clean_copy` (strips em dashes — house style), `smart_summary(text, max_chars=280)`,
`bold_key_data`, `sec_div`, `tab_summary`, `sec_intel`, `empty_state(icon, title, body)`, `tab_intro`,
`callout(icon, headline, body, style="teal")`, `chart_primer`, `source_card`, `grain_badge`, `_sh`,
`generate_section_html`, `generate_board_report_html`, `render_smart_insight_card`, `insight_card`, `kpi_card`,
`event_stat`, `_h_delta_html`.

*SVG:* `kpi_metric_svg`, `sparkline_svg(values, positive=True, width=120, height=28)`, `insight_icon_svg`,
`event_icon_svg`.

*Charts:* `render_occ_heatmap`, `render_comp_set_radar`, `render_adr_gas_scatter`, `render_dma_bubble_map`,
`render_feeder_sankey`, `render_booking_pace`, `render_content_funnel`, `render_painted_occ_heatmap`,
`render_share_bar`, `render_kpi_ticker`, `style_fig(fig, height=360)`.

*Control/infra:* `_safe_section(fn, section_name)`, `_tab_controls(tab_id, show_filter_badge=True)`,
`_str_filters(tab_id, show_grain=True, show_metric=True)`, `render_intel_panel`, `_render_login_page`.

### 3f. Half-finished / dormant

- **`_render_login_page()`** (`app.py:166`) — a complete login UI, permanently disabled by
  `_LOGIN_ENABLED = False` (`app.py:164`, comment: *"Login removed per owner request, admin controls at ?admin=true"*).
  ~100 lines of dead but maintained UI. `streamlit-authenticator` stays in `requirements.txt` for it.
- **`fetch_godly_design.py`** — pipeline step whose purpose is not evident from the name; **[INFERRED]** a design-asset
  fetcher, likely experimental.
- **`events_insights` table** — exists, **0 rows**; nothing populates it.
- **`airbnb_market_data` table** — exists, **0 rows**; `airbnb_market_summary` (48 rows) is what's actually used.

### 3g. Navigation structure (`app.py:10015–10037`)

Six top-level tabs, three with sub-tabs. A comment notes these were consolidated down from 10 peer tabs, and that
sub-tab variables **deliberately reuse the original variable names** so the (very long) render blocks below needed no
edits:

```
🏠 Today's Overview       tab_ov        → 4 sub-tabs @ app.py:10539
🏨 Hotel Performance      tab_hotels    → 🏨 Hotel Trends (tab_tr) · 🛎️ Group Lodging (tab_gt) · 🏗️ New Competition (tab_sp)
👥 Visitors & Events      tab_visitors  → 👥 Our Visitors (tab_ev) · 🗺️ Where They're From (tab_fm) · 🎉 Event Impact (tab_ei)
🔮 What's Next            tab_fo        → audience tabs @ app.py:12398 (driven by AUDIENCE_CONFIG)
📈 Market Intel           tab_cs        → 📊 Market Performance · 📡 External Signals @ app.py:16147
🗄️ Data & Downloads       tab_dl
```

Deep-linking to a tab is done by injecting JavaScript that **clicks the tab element after a 100 ms `setTimeout`**
(`app.py:10039–10051`). This is timing-dependent and will silently no-op on a slow render. **[INFERRED]** it exists
because Streamlit has no API for programmatic tab selection.

---

## 4. Data layer

### 4a. Where data comes from

**Nothing is fetched at render time.** The dashboard is a **read-only consumer of one SQLite file**,
`data/analytics.sqlite` (7.9 MB, **120 tables**, committed to git). All writes happen out-of-band in
`scripts/run_pipeline.py`. The dashboard makes exactly one outbound network call class: the AI Analyst provider APIs.

```
Raw sources                          ETL (scripts/)                 Store                    Read
────────────────────────────────────────────────────────────────────────────────────────────────────────
data/str/*.xlsx (gitignored)   →  load_str_daily/monthly_sqlite  ┐
data/datafy/**.csv             →  load_datafy_reports            │
data/costar/**.pdf|csv         →  load_costar_reports            │
data/Zartico/**.pdf            →  load_zartico_reports           ├→  data/analytics.sqlite  →  app.py loaders
data/later/{IG,FB,TikTok}/*.CSV→  load_later_reports             │   (120 tables, 7.9 MB)      (@st.cache_data)
data/us_travel/ · Visit_California/ → load_us_travel / load_visit_ca* │
~30 public HTTP APIs           →  fetch_*.py                     ┘
                                        ↓
                       compute_kpis.py → compute_insights.py → build_table_relationships.py
```

### 4b. Connection layer (`app.py:4321–4556`)

One `sqlite3` connection for the whole session, built by `_open_connection()` (`@st.cache_resource`) and always
retrieved through `get_connection()`, which is **self-healing**: it runs `SELECT 1` and rebuilds via
`_open_connection.clear()` if the handle was closed.

Read PRAGMAs applied on open (`_READ_PRAGMAS`): `journal_mode=WAL`, `synchronous=NORMAL`, `temp_store=MEMORY`,
`cache_size=-16000` (16 MB), `mmap_size=134217728` (128 MB), `busy_timeout=10000`.

Hot-path indexes (`_HOT_INDEXES`, created idempotently at startup and again by `scripts/optimize_db.py`):
`idx_str_src_grain_date` on `fact_str_metrics(source, grain, as_of_date)`; `idx_str_metric` on
`fact_str_metrics(metric_name)`; `idx_kpi_daily_date`; `idx_insights_aud_date`; `idx_load_log_run`.

Every loader funnels through `_sql(query, ttl_hint="")` (`app.py:4548`), which **swallows all exceptions and returns
an empty DataFrame**, logging at `DEBUG` to the `vdp_dashboard` logger. This is the single most important thing to
know when debugging: **a blank panel means a thrown query, not missing data.** See §7.

Cache TTL tiers: real-time KPIs **300 s**, social/campaign **1800 s**, historical (Zartico / Visit California)
**3600 s**, `load_strategy_goals` **60 s**.

### 4c. Datasets — exact fields and types

Types are the SQLite declared types. **All sample rows below use realistic dummy values — no real proprietary
figures appear in this document.** Structure, formats, and enumerations are real.

---

#### `fact_str_metrics` — Layer 1 truth, long format (6,910 rows)

| Field | Type | Notes |
|---|---|---|
| `source` | TEXT | Only value present: `'STR'` |
| `grain` | TEXT | `'daily'` \| `'monthly'` |
| `property_name` | TEXT | Only value present: `'VDP Select Portfolio'` |
| `market` | TEXT | Only value present: **`'Anaheim Area'`** — see the warning below |
| `submarket` | TEXT | Always `NULL` in current data |
| `as_of_date` | TEXT | `YYYY-MM-DD` |
| `metric_name` | TEXT | `supply` \| `demand` \| `revenue` \| `occ` \| `adr` \| `revpar` |
| `metric_value` | REAL | `occ` is a **decimal** (0.688 = 68.8%); money in USD; supply/demand in room-nights. Negatives stored as `NULL`, never floored to 0. |
| `unit` | TEXT | e.g. `'rooms'`, `'USD'` |

Dedup key: `(source, grain, property_name, market, as_of_date, metric_name)`.
Coverage: **daily 2024-02-28 → 2026-03-28** (4,560 rows) · **monthly 1987-01-01 → 2026-02-01** (2,350 rows).

⚠️ **`market` is `'Anaheim Area'` for every row.** `CLAUDE.md` states in bold that *"STR comp set market is Dana
Point, NOT Anaheim … Never default to 'Anaheim Area' — that is wrong."* The rule is in the project memory but the
data itself contradicts it. **[INFERRED]** the STR export carries the parent market label and the loader passes it
through unchanged; the correct comp-set markets live in `fact_str_group_metrics` instead. Confirm with John before
surfacing `market` anywhere user-facing.

```
{'source':'STR','grain':'daily','property_name':'VDP Select Portfolio','market':'Anaheim Area',
 'submarket':None,'as_of_date':'2025-06-14','metric_name':'supply','metric_value':1800.0,'unit':'rooms'}
{'source':'STR','grain':'daily','property_name':'VDP Select Portfolio','market':'Anaheim Area',
 'submarket':None,'as_of_date':'2025-06-14','metric_name':'occ','metric_value':0.742,'unit':'ratio'}
{'source':'STR','grain':'daily','property_name':'VDP Select Portfolio','market':'Anaheim Area',
 'submarket':None,'as_of_date':'2025-06-14','metric_name':'adr','metric_value':340.00,'unit':'USD'}
```

---

#### `kpi_daily_summary` — wide daily KPIs (760 rows, 2024-02-28 → 2026-03-28)

| Field | Type | Notes |
|---|---|---|
| `as_of_date` | TEXT PK | `YYYY-MM-DD` |
| `occ_pct` | REAL | **Percentage** (68.8), not decimal — differs from `fact_str_metrics.occ` |
| `adr` · `revpar` | REAL | USD |
| `occ_yoy` · `adr_yoy` · `revpar_yoy` | REAL | % change vs same calendar date prior year. **NULL for 366 of 760 rows** (no prior-year date). |
| `occ_pct_yoy_pp` · `adr_yoy_pct` · `revpar_yoy_pct` | REAL | **DEAD — 0 of 760 rows populated.** Legacy columns retained by the migration path. |
| `is_occ_80` · `is_occ_90` | INTEGER | `1`/`0` compression flags |
| `created_at` | TEXT | `YYYY-MM-DD HH:MM:SS` |

```
{'as_of_date':'2025-06-14','occ_pct':74.2,'adr':340.00,'revpar':252.28,'created_at':'2026-06-29 15:39:31',
 'occ_pct_yoy_pp':None,'adr_yoy_pct':None,'revpar_yoy_pct':None,
 'occ_yoy':4.10,'adr_yoy':6.20,'revpar_yoy':10.55,'is_occ_80':0,'is_occ_90':0}
{'as_of_date':'2025-06-15','occ_pct':91.4,'adr':395.00,'revpar':361.03,'created_at':'2026-06-29 15:39:31',
 'occ_pct_yoy_pp':None,'adr_yoy_pct':None,'revpar_yoy_pct':None,
 'occ_yoy':7.80,'adr_yoy':5.10,'revpar_yoy':13.30,'is_occ_80':1,'is_occ_90':1}
```

---

#### `kpi_compression_quarterly` (9 rows)

`quarter` TEXT PK (`'2025-Q3'`) · `days_above_80_occ` INTEGER · `days_above_90_occ` INTEGER · `created_at` TEXT.

```
{'quarter':'2025-Q2','days_above_80_occ':28,'days_above_90_occ':9,'created_at':'2026-06-29 15:39:31'}
{'quarter':'2025-Q3','days_above_80_occ':41,'days_above_90_occ':22,'created_at':'2026-06-29 15:39:31'}
```

---

#### `fact_str_group_metrics` — comp-set + segment mix (4,968 rows)

`source` TEXT · `grain` TEXT (`'weekly'`) · `as_of_date` TEXT · `market` TEXT · `segment` TEXT ·
`metric_name` TEXT · `metric_value` REAL · `unit` TEXT · `data_period` TEXT (`'current'` \| comparison label).

- **`market` enum (6, the real comp set):** `Dana Point`, `Newport Beach`, `La Jolla`, `Santa Barbara`,
  `Monterey-Carmel`, `Huntington Beach`.
- **`segment` enum (5):** `Total`, `Trans.` (transient), `Grp.` (group), `Con.`, `Cont.`
  **[INFERRED]** `Con.` = Contract and `Cont.` = Contract-Other, or one is an ingestion artifact of the other —
  the loader does not document them and both appear in live data. Worth verifying before charting segment mix.
- **`metric_name` enum (6):** `supply`, `demand`, `revenue`, `adr`, `occ_pct`, `revpar`.
- ⚠️ `occ_pct` here is a **percentage** (56.78), unlike `fact_str_metrics.occ` which is a decimal.

```
{'source':'STR','grain':'weekly','as_of_date':'2025-12-28','market':'Dana Point','segment':'Trans.',
 'metric_name':'occ_pct','metric_value':56.78,'unit':'%','data_period':'current'}
{'source':'STR','grain':'weekly','as_of_date':'2025-12-28','market':'Dana Point','segment':'Grp.',
 'metric_name':'occ_pct','metric_value':9.75,'unit':'%','data_period':'current'}
```

---

#### `insights_daily` — the "brain" output (793 rows)

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `as_of_date` | TEXT | Latest: **2026-07-02** |
| `audience` | TEXT | `dmo` (203) · `cross` (259) · `city` (122) · `visitor` (109) · `resident` (100) |
| `category` | TEXT | 36 distinct categories on the latest run |
| `headline` | TEXT | One line; `cross` insights are prefixed `HIDDEN SIGNAL/OPPORTUNITY/RISK/GAP` |
| `body` | TEXT | Long form, structured as `… \| WHO: … \| WHAT: … \| WHEN: … \| WHERE: … \| WHY: … \| HOW: …` |
| `metric_basis` | TEXT | **JSON string** — must be `json.loads`-ed, not read as a dict |
| `priority` | INTEGER | 1 = highest |
| `horizon_days` | INTEGER | Forward-looking window |
| `data_sources` | TEXT | Comma-separated table names |
| `created_at` | TEXT | |

Unique key: `(as_of_date, audience, category)`, UPSERT — safe to re-run same-day.

```
{'id':1,'as_of_date':'2026-07-02','audience':'dmo','category':'demand_trend',
 'headline':'RevPAR stable at $250.00 (30-day avg); YOY +8.0% — shoulder position',
 'body':'The trailing 30-day average RevPAR is $250.00, with ADR at $355.00 and occupancy at 70.4%. '
        'Year-over-year RevPAR growth is +8.0%, signaling a healthy pricing environment. '
        '| WHO: VDP TBID board, hotel revenue managers | WHAT: RevPAR $250.00 (+8.0% YOY), 6 compression days QTD '
        '| WHEN: Next 30 days | WHERE: Dana Point select portfolio | WHY: sets TBID revenue narrative '
        '| HOW: Maintain rate discipline and lock 2-night minimums on compression dates.',
 'metric_basis':'{"avg_revpar_30d": 250.00, "avg_adr_30d": 355.00, "avg_occ_30d": 70.4, '
                '"avg_revpar_yoy_30d": 8.0, "trend": "flat", "comp_80_qtd": 6}',
 'priority':1,'horizon_days':30,'data_sources':'kpi_daily_summary,kpi_compression_quarterly',
 'created_at':'2026-07-02 06:47:27'}
```

---

#### `datafy_overview_dma` — feeder markets (14 rows)

`id` INTEGER · `report_period_start`/`report_period_end` TEXT · `dma` TEXT · `visitor_days_share_pct` REAL ·
`visitor_days_vs_compare_pct` REAL · `spending_share_pct` REAL · `avg_spend_usd` REAL ·
`avg_length_of_stay_days` REAL (**all NULL in current data**) · `trips_share_pct` REAL (**all NULL**) ·
`loaded_at` TEXT.

```
{'id':673,'report_period_start':'2025-01-01','report_period_end':'2025-12-31','dma':'Los Angeles',
 'visitor_days_share_pct':19.00,'visitor_days_vs_compare_pct':-0.2,'spending_share_pct':16.00,
 'avg_spend_usd':205.00,'avg_length_of_stay_days':None,'trips_share_pct':None,'loaded_at':'2026-06-29 15:39:31'}
{'id':674,'report_period_start':'2025-01-01','report_period_end':'2025-12-31','dma':'San Diego',
 'visitor_days_share_pct':8.00,'visitor_days_vs_compare_pct':0.2,'spending_share_pct':6.50,
 'avg_spend_usd':185.00,'avg_length_of_stay_days':None,'trips_share_pct':None,'loaded_at':'2026-06-29 15:39:31'}
```

⚠️ Two of nine columns are entirely NULL. Any chart binding `avg_length_of_stay_days` or `trips_share_pct` renders
empty with no error.

---

#### `datafy_overview_kpis` — annual visitor overview (**1 row**, 29 columns)

Key fields (all REAL unless noted): `report_title` TEXT, `report_period_start`/`_end` TEXT,
`compare_period_start`/`_end` TEXT, `data_source` TEXT, `total_trips` INTEGER, `avg_length_of_stay_days`,
`avg_los_vs_compare_days`, `day_trips_pct`, `day_trips_vs_compare_pct`, `overnight_trips_pct`,
`overnight_vs_compare_pct`, `one_time_visitors_pct`, `repeat_visitors_pct`, `in_state_visitor_days_pct`,
`in_state_vd_vs_compare_pct`, `out_of_state_vd_pct`, `out_of_state_vd_vs_compare_pct`, `in_state_spending_pct`,
`out_of_state_spending_pct`, `locals_pct`, `locals_vs_compare_pct`, `visitors_pct`, `visitors_vs_compare_pct`,
`local_spending_pct`, `visitor_spending_pct`, `total_trips_vs_compare_pct`, `loaded_at` TEXT.

**Single-row table** — every consumer must guard `.iloc[0]` against an empty frame.

---

#### `group_intelligence` — group benchmark model (8 rows, 27 columns)

`benchmark_date`, `total_market_rooms` INT, `group_primary_rooms` INT, `group_primary_pct`,
`benchmark_group_demand_share_low`/`_high`, `benchmark_group_adr_discount_pct`, `market_blended_adr`,
`market_blended_occ_pct`, `estimated_group_adr`, `estimated_annual_room_rev`,
`estimated_group_room_rev_low`/`_high`, `estimated_group_tbid_rev_low`/`_high`,
`estimated_group_tot_rev_low`/`_high`, `tbid_uplift_per_5pp_shift`, `compression_days_annual` INT,
`group_displacement_note` TEXT, `str_group_demand_rooms` INT, `str_group_adr`, `str_group_room_rev`,
`str_group_data_available` INT (0/1 flag), `data_sources` TEXT, `notes` TEXT, `loaded_at` TEXT.

⚠️ Populated by `scripts/seed_group_benchmarks.py` — these are **modeled/seeded estimates, not measured Layer 1
data**, despite feeding board-facing TBID figures. `str_group_data_available` is the flag distinguishing modeled from
real. Treat every `estimated_*` column as an assumption.

---

#### `events_economic_impact` (22 rows, 25 columns)

`event_id` INT, `event_date` TEXT, `event_name` TEXT, then paired baseline/event/lift triples:
`baseline_occupancy`/`event_occupancy`/`occ_lift_pct`, `baseline_adr`/`event_adr`/`adr_lift_pct`,
`baseline_revpar`/`event_revpar`/`revpar_lift_pct`; plus `estimated_rooms_sold` INT, `estimated_room_revenue`,
`estimated_total_spend`, `visitor_days_generated` INT, `daytrip_conversions` INT, `overnight_conversion_pct`,
`estimated_tbid_revenue`, `estimated_tot_revenue`, `event_marketing_cost`, `estimated_roi`,
`revenue_per_attendee`, `calculated_at` TEXT.

---

#### `vdp_events` (19 rows)

`id`, `event_name` TEXT, `event_date` TEXT, `event_end_date` TEXT, `category` TEXT, `venue` TEXT,
`description` TEXT, `url` TEXT, `is_major` INTEGER, `scraped_at` TEXT. Unique on `(event_name, event_date)`.

```
{'id':1,'event_name':'Ohana Fest','event_date':'2025-09-26','event_end_date':'2025-09-28',
 'category':'Festival/Concert','venue':'Doheny State Beach',
 'description':'Annual music and surf festival. Signature demand compression event.',
 'url':'https://visitdanapoint.com/events/','is_major':1,'scraped_at':'2026-06-29 15:40:01'}
{'id':2,'event_name':'OC Marathon','event_date':'2025-05-04','event_end_date':'2025-05-04',
 'category':'Race/Sport','venue':'Dana Point Harbor',
 'description':'Annual marathon finishing at Dana Point Harbor.',
 'url':'https://visitdanapoint.com/events/','is_major':1,'scraped_at':'2026-06-29 15:40:01'}
```

**[INFERRED]** The VDP events calendar is JavaScript-rendered, so `fetch_vdp_events.py` seeds known major events as a
fallback rather than truly scraping (stated in `CLAUDE.md`).

---

#### `load_log` — ETL audit trail (2,243 rows)

`id` INT PK · `source` TEXT · `grain` TEXT · `file_name` TEXT · `rows_inserted` INT · `run_at` TEXT.

```
{'id':1,'source':'STR','grain':'daily','file_name':'str_daily.xlsx','rows_inserted':4392,'run_at':'2026-03-09 19:49:32'}
{'id':2,'source':'STR','grain':'daily','file_name':'str_daily.xlsx','rows_inserted':0,'run_at':'2026-03-09 20:03:40'}
```

Note `rows_inserted: 0` is normal and expected — loaders are idempotent, so a re-run inserts nothing.

---

#### `strategy_goals` (8 rows) · `table_relationships` (329 rows) · `zartico_*` (8 tables)

- `strategy_goals`: `title`, `description`, `category` (`revenue`/`visitors`/`occupancy`/`tbid`/`marketing`/`social`/
  `custom`), `metric_name`, `metric_unit`, `target_value`, `current_value`, `baseline_value`, `start_date`,
  `target_date`, `status`, `priority` INT, `notes`, `auto_compute` INT, `compute_query` TEXT, `created_at`,
  `updated_at`. ⚠️ **`compute_query` stores raw SQL executed by `compute_strategy_progress.py`** — if goals are ever
  made user-editable, that is a SQL injection surface.
- `table_relationships`: `table_a`, `table_b`, `relationship_type`, `join_key`, `description`, `created_at`.
  The column is **`created_at`, not `updated_at`** (a documented past bug).
- `zartico_*`: **Layer 1.5 historical reference — a June 2025 snapshot.** Per `CLAUDE.md`, must never be presented as
  current data; it exists to tell the growth story.

### 4d. Full table census (120 tables)

<details><summary>Row counts as of this briefing</summary>

`airbnb_market_data` 0 · `airbnb_market_summary` 48 · `airnow_aqi_daily` 124 · `beach_water_quality_weekly` 574 ·
`bls_employment_monthly` 308 · `bts_route_passengers` 68 · `ca_state_parks_visitation` 174 ·
`census_demographics` 72 · `costar_annual_performance` 48 · `costar_chain_scale_breakdown` 12 ·
`costar_competitive_set` 9 · `costar_market_snapshot` 60 · `costar_monthly_performance` 24 ·
`costar_profitability` 59 · `costar_supply_pipeline` 6 · `data_correlation_matrix` 6 ·
`datafy_attribution_media_groups` 3 · `datafy_attribution_media_kpis` 2 ·
`datafy_attribution_media_top_markets` 106 · `datafy_attribution_peak_visitation` 84 ·
`datafy_attribution_polygons` 7 · `datafy_attribution_website_channels` 3 ·
`datafy_attribution_website_clusters` 20 · `datafy_attribution_website_demographics` 25 ·
`datafy_attribution_website_dma` 9 · `datafy_attribution_website_groups` 3 ·
`datafy_attribution_website_kpis` 1 · `datafy_attribution_website_market_performance` 11 ·
`datafy_attribution_website_media_breakdown` 3 · `datafy_attribution_website_top_markets` 12 ·
`datafy_attribution_website_visitor_markets` 11 · `datafy_overview_airports` 10 ·
`datafy_overview_category_spending` 10 · `datafy_overview_cluster_visitation` 9 ·
`datafy_overview_demographics` 12 · `datafy_overview_dma` 14 · `datafy_overview_kpis` 1 ·
`datafy_overview_spending_by_category` 11 · `datafy_overview_spending_by_market` 13 ·
`datafy_overview_top_markets` 20 · `datafy_overview_top_pois` 10 · `datafy_overview_total_kpis` 1 ·
`datafy_social_audience_overview` 1 · `datafy_social_device_breakdown` 3 · `datafy_social_ga_channels` 9 ·
`datafy_social_ga_overview` 1 · `datafy_social_geo_breakdown` 4310 · `datafy_social_new_vs_returning` 1 ·
`datafy_social_top_pages` 99 · `datafy_social_top_searches` 117 · `datafy_social_traffic_sources` 26 ·
`demand_signal_weekly` 67 · `eia_gas_prices` 1137 · `events_economic_impact` 22 · **`events_insights` 0** ·
`events_metrics` 22 · `events_promotion_analysis` 22 · `events_visitor_mix` 22 · `fact_str_group_metrics` 4968 ·
`fact_str_metrics` 6910 · `fact_str_response_markets` 5777 · `fred_economic_indicators` 794 ·
`google_trends_weekly` 1166 · `group_intelligence` 8 · `insights_daily` 793 · `kpi_compression_quarterly` 9 ·
`kpi_daily_summary` 760 · `later_fb_posts` 42 · `later_fb_profile_growth` 102 ·
`later_fb_profile_interactions` 102 · `later_ig_audience_demographics` 3 · `later_ig_audience_engagement` 336 ·
`later_ig_location` 11 · `later_ig_posts` 50 · `later_ig_profile_growth` 134 · `later_ig_reels` 16 ·
`later_ig_stories` 388 · `later_tk_audience_demographics` 9 · `later_tk_audience_engagement` 336 ·
`later_tk_interactions` 134 · `later_tk_profile_growth` 134 · `load_log` 2243 · `noaa_marine_monthly` 10 ·
`noaa_tides_daily` 146 · `socal_gas_prices` 52 · `str_holiday_calendar` 133 · `strategy_goals` 8 ·
`stvr_market_summary` 12 · `surf_conditions_daily` 168 · `table_relationships` 329 · `ticketmaster_events` 8 ·
`tsa_checkpoint_daily` 39 · `us_travel_business_travel` 5 · `us_travel_group_segments` 7 ·
`us_travel_national_kpis` 10 · `us_travel_traveler_types` 10 · `vdp_events` 19 · `visit_ca_airport_traffic` 120 ·
`visit_ca_intl_arrivals` 37 · `visit_ca_intl_market_profiles` 13 · `visit_ca_lodging_forecast` 143 ·
`visit_ca_lodging_monthly` 45 · `visit_ca_travel_forecast` 22 · `visit_ca_travel_indicators` 8 ·
`weather_forecast` 32 · `weather_hourly` 127 · `weather_monthly` 78 · `weather_observations` 1120 ·
`whale_watching_activity` 539 · `wikipedia_pageviews_daily` 2433 · `zartico_event_impact` 1 ·
`zartico_future_events_summary` 1 · `zartico_kpis` 35 · `zartico_lodging_kpis` 1 · `zartico_markets` 11 ·
`zartico_movement_monthly` 10 · `zartico_overnight_trend` 13 · `zartico_spending_monthly` 11 ·
plus `sqlite_sequence` 78, `sqlite_stat1` 121 (internal).

</details>

### 4e. Data freshness — currently stale

| Series | Latest value | Age at briefing (2026-07-27) |
|---|---|---|
| STR daily (`fact_str_metrics`, `kpi_daily_summary`) | **2026-03-28** | ~4 months |
| STR monthly | **2026-02-01** | ~6 months |
| `insights_daily` (last pipeline run) | **2026-07-02** | ~3.5 weeks |
| `kpi_daily_summary.created_at` | 2026-06-29 | ~4 weeks |

The insights engine ran a month after the newest STR data. Every "30-day" and "trailing" metric in §5 is therefore
computed over a window ending in **March**, while the UI labels them as current. **This is the single biggest
correctness risk for a demo.** Verify with John whether the STR feed is broken or simply paused.

---

## 5. Metrics already implemented

### 5a. Computed in SQL — `scripts/compute_kpis.py`

Both tables are **fully rebuilt** (`DELETE` + `INSERT`) on every run.

**`kpi_daily_summary`** — one CTE-based INSERT (verbatim logic):

```sql
WITH base AS (
    SELECT as_of_date,
        MAX(CASE WHEN metric_name = 'occ'    THEN metric_value * 100 END) AS occ_pct,
        MAX(CASE WHEN metric_name = 'adr'    THEN metric_value END)       AS adr,
        MAX(CASE WHEN metric_name = 'revpar' THEN metric_value END)       AS revpar
    FROM fact_str_metrics WHERE grain = 'daily' AND source = 'STR'
    GROUP BY as_of_date
)
SELECT b.as_of_date, b.occ_pct, b.adr, b.revpar,
    CASE WHEN ly.occ_pct > 0 THEN ROUND((b.occ_pct - ly.occ_pct) / ly.occ_pct * 100, 2) END AS occ_yoy,
    CASE WHEN ly.adr    > 0 THEN ROUND((b.adr    - ly.adr)    / ly.adr    * 100, 2) END AS adr_yoy,
    CASE WHEN ly.revpar > 0 THEN ROUND((b.revpar - ly.revpar) / ly.revpar * 100, 2) END AS revpar_yoy,
    CASE WHEN b.occ_pct >= 80 THEN 1 ELSE 0 END AS is_occ_80,
    CASE WHEN b.occ_pct >= 90 THEN 1 ELSE 0 END AS is_occ_90
FROM base b
LEFT JOIN base ly ON ly.as_of_date = date(b.as_of_date, '-1 year');
```

- `occ_pct` = decimal × 100. `occ_yoy` is a **percent change**, not a percentage-point delta — despite the dead
  legacy column being named `occ_pct_yoy_pp` ("pp"). **[INFERRED]** the metric definition was changed from
  percentage-points to percent-change at some point and the old columns were orphaned rather than dropped.
- `date(b.as_of_date, '-1 year')` on **Feb 29** yields Feb 28 in SQLite; leap-day rows compare against a
  non-corresponding date. Minor, but real.

**`kpi_compression_quarterly`:**

```sql
SELECT strftime('%Y', as_of_date) || '-Q' ||
       CAST((CAST(strftime('%m', as_of_date) AS INTEGER) + 2) / 3 AS TEXT) AS quarter,
    SUM(CASE WHEN occ_pct > 80 THEN 1 ELSE 0 END) AS days_above_80_occ,
    SUM(CASE WHEN occ_pct > 90 THEN 1 ELSE 0 END) AS days_above_90_occ
FROM kpi_daily_summary WHERE occ_pct IS NOT NULL GROUP BY quarter;
```

🔴 **Threshold inconsistency (real bug).** `is_occ_80` / `is_occ_90` use **`>=`**; the quarterly rollup uses **`>`**.
A day at exactly 80.0% or 90.0% is flagged as compression in `kpi_daily_summary` but **not counted** in
`kpi_compression_quarterly`. The two tables will disagree, and both are surfaced on the Overview tab.

### 5b. Computed in Python — `build_metrics_context()` (`app.py:5524–5620`)

Feeds the AI prompt and several UI cards. `pct_delta(a, b) = (a - b) / b * 100 if b else 0.0`.

| Metric | Formula as written |
|---|---|
| `revpar_30` / `adr_30` / `occ_30` | `df.tail(30)[col].mean()` |
| `revpar_90` | `df.tail(90)["revpar"].mean()` |
| `rev_30_total` | `df.tail(30)["revenue"].sum()` |
| `demand_30` | `df.tail(30)["demand"].sum()` |
| `revpar_delta` / `adr_delta` / `occ_delta` | `pct_delta(recent_half.mean(), prior_half.mean())` where the split is `half = len(df) // 2` |
| `weekend_revpar` / `weekend_occ` | mean over `dayofweek.isin([4, 5])` → **Friday + Saturday** |
| `midweek_revpar` / `midweek_occ` | mean over `dayofweek.isin([1, 2])` → **Tuesday + Wednesday** |
| **`tbid_monthly`** | `df.tail(30)["revenue"].sum() * 0.0125` |
| **`tbid_12m`** | `df_mon.tail(12)["revenue"].sum() * 0.0125` |
| **`tbid_ytd`** | `sum(revenue where year == current_year) * 0.0125` |
| **`tbid_ytd_prior`** | `sum(revenue where year == current_year-1 AND dayofyear <= today.dayofyear) * 0.0125` |
| `tbid_ytd_yoy` | `pct_delta(ytd_rev, prior_rev) if prior_rev > 0 else 0.0` |
| `n_spikes` | `(revpar > mean + 2*std).sum()` |
| `n_drops` | `(revpar < mean - 1.5*std).sum()` — **asymmetric with `n_spikes` by design** |
| `revpar_12m` / `adr_12m` / `occ_12m` | `df_mon.tail(12)[col].mean()` |
| `*_yoy_12m` | `pct_delta(last_12m_mean, df_mon.iloc[-24:-12].mean())` |
| `comp_recent_q` / `comp_prior_q` | `df_comp.iloc[-1]` / `.iloc[-2]` `["days_above_90_occ"]` |

🔴 **Bug — `revpar_best_month` / `revpar_best_val` are never populated** (`app.py:5613–5619`).
The block is indented **inside the `except Exception: pass` suite** of the TBID-YTD `try`:

```python
    except Exception:
        pass

        # Best month by RevPAR in the last 12 months     ← dead code
        best_idx = m12["revpar"].idxmax()
        ctx["revpar_best_month"] = m12.loc[best_idx, "as_of_date"].strftime("%b %Y")
        ctx["revpar_best_val"]   = float(m12.loc[best_idx, "revpar"])
```

Consequences: (1) on the happy path these lines never run, so both keys keep their `""` / `0.0` initializers and any
"best month" display shows blank/zero; (2) if the TBID-YTD block *does* raise, these lines run inside the handler and
reference `m12`, which is **undefined** whenever `df_mon` was empty or under 12 rows — raising `NameError` out of the
`except`, which nothing catches. **[INFERRED]** an editing accident: the block was written for the monthly `if` above
and lost its indentation when the TBID-YTD section was inserted between them.

🔴 **`tbid_ytd_prior` is not a like-for-like comparison.** It filters prior-year rows to `dayofyear <= today`, but
`tbid_ytd` applies **no day-of-year cap** to the current year. With the data ending 2026-03-28 and "today" being late
July, current YTD covers Jan–Mar while prior YTD covers Jan–late-July. The resulting `tbid_ytd_yoy` is **structurally
wrong** and will read as a catastrophic decline. This compounds the staleness in §4e.

### 5c. Hardcoded business constants

| Constant | Value | Location | Status |
|---|---|---|---|
| TBID blended assessment rate | **`0.0125`** (1.25%) | Inline at `app.py:5561`, `5590`, `5610`, `5611` | **Hardcoded, 4 duplicate literals — no named constant** |
| TOT rate | **`0.10`** | `SYSTEM_PROMPT` prose + ETL | Documented; `TOT Revenue = Room Revenue × 0.10` |
| TBID tiers | ≤$199.99 → 1.0% · $200–$399.99 → 1.5% · ≥$400 → 2.0% | `CLAUDE.md` + `SYSTEM_PROMPT` | **Never implemented in code** — only the blended 1.25% is used |
| `OCC_HIGH_THRESHOLD` | `0.90` | `app.py:281` | 🔴 **Defined but never referenced** |
| `OCC_MED_THRESHOLD` | `0.80` | `app.py:282` | 🔴 **Defined but never referenced** |
| `OCC_SHOULDER_TARGET` | `0.65` | `app.py:283` | 🔴 **Defined but never referenced** |
| Monthly seasonality index | `{6:1.18, 7:1.25, 8:1.22, 9:1.10, 10:1.05, 11:0.90, 12:0.88}` | `app.py:12585` | Hardcoded magic dict, no provenance comment |
| Ohana Fest reference figures | $14.6M expenditure · $18.4M destination spend · $139 ADR lift · $1,219 accom/trip · 68% OOS · 3.2× multiplier | `CLAUDE.md`, `SYSTEM_PROMPT` | Static reference constants |

🔴 **The three `OCC_*` constants are dead.** `CLAUDE.md` claims they exist "instead of hardcoded 0.90/0.80/0.65 magic
numbers," but a full-file search finds **zero usages**. Every real threshold check is still a literal, and they are
inconsistent in both scale and operator:

- `app.py:7457` — `if v >= 90:` (percent scale)
- `app.py:7458` — `if v >= 80:` (percent scale)
- `app.py:11070` — `if _tr_occ_v >= 80` (percent scale)
- `app.py:12549` — `_kdf["is_comp"] = (_kdf["occ_pct"] >= 80).astype(int)` (percent scale)
- `app.py:12759` — `"#F43F5E" if v >= 80 else "#F59E0B" if v >= 70 else "#00C8E0"` — introduces an **undocumented
  third tier at 70** that appears nowhere in the business rules
- `compute_kpis.py` — `>= 80` / `>= 90` in one query, `> 80` / `> 90` in the other

So "compression" is defined **four different ways** across the codebase. Reconciling this is the highest-value
correctness cleanup available.

### 5d. Modeled (not measured) metrics

Everything in `group_intelligence` prefixed `estimated_*` — group room revenue, group TBID/TOT low/high bands, and
`tbid_uplift_per_5pp_shift` — is produced by `scripts/seed_group_benchmarks.py` from national benchmark shares, not
from STR group data. `str_group_data_available` (0/1) is the flag. `SYSTEM_PROMPT` states these as board-facing facts
("Est. $3.6M–$4.6M annual TBID from group demand"; "+5pp shift adds ~$180K"). **Label these as modeled in any
board-facing output.**

Similarly `events_economic_impact.estimated_roi`, `revenue_per_attendee`, and `daytrip_conversions` are derived
estimates, and the six `cross`-audience insights combine STR × Datafy assumptions by design (they return empty if
either source is missing).

---

## 6. Design system

### 6a. Tokens

The app defines CSS custom properties on `:root`. **The live values are the LIGHT set, defined inline at
`app.py:734–761`:**

| Token | Light (live, `app.py`) | Dark (`assets/styles.css`, **dead**) |
|---|---|---|
| `--dp-bg` | `#FFFFFF` | `#0E1B2A` |
| `--dp-bg2` | `#F8FAFC` | `#122133` |
| `--dp-surface` | `#F1F5F9` | `#192D42` |
| `--dp-card` / `--dp-card-solid` | `#FFFFFF` | `#1E3550` |
| `--dp-card-hover` | `#F8FAFC` | `#243D5C` |
| `--dp-border` | `#E2E8F0` | `rgba(255,255,255,0.18)` |
| `--dp-border-accent` | `#0EA5E9` | `rgba(0,212,200,0.50)` |
| `--dp-teal` | `#0891B2` | `#00D4C8` |
| `--dp-teal-dim` / `--dp-teal-glow` | `rgba(8,145,178,.10)` / `.20` | `rgba(0,212,200,.18)` / `.32` |
| `--dp-blue` | `#0284C7` | `#38BDF8` |
| `--dp-green` | `#059669` | `#10B981` |
| `--dp-amber` | `#D97706` | `#F5B940` |
| `--dp-red` | `#DC2626` | `#EF4444` |
| `--dp-purple` | `#7C3AED` | `#A78BFA` |
| `--dp-orange` | `#EA580C` | `#FB923C` |
| `--dp-text-1…4` | `#0F172A` / `#334155` / `#64748B` / `#94A3B8` | `#F4FAFF` / `#C8E0F2` / `#8EC4DC` / `#5A8AAA` |
| `--dp-radius` / `--dp-radius-lg` | `8px` / `12px` | `12px` / `16px` |
| `--dp-shadow` | `0 1px 3px rgba(15,23,42,.12), 0 1px 2px rgba(15,23,42,.24)` | `0 1px 4px rgba(0,0,0,.22), 0 4px 20px rgba(0,0,0,.16)` |
| `--dp-shadow-hover` | `0 4px 12px rgba(15,23,42,.15), 0 2px 4px rgba(15,23,42,.10)` | `0 8px 32px rgba(0,0,0,.28), 0 0 0 1px rgba(0,212,200,.22)` |
| `--dp-shadow-deep` | `0 10px 25px rgba(15,23,42,.15)` | `0 16px 48px rgba(0,0,0,.36)` |

**A completely separate Python-level palette also exists** (`app.py:270–278`) and is passed directly to Plotly, which
cannot read CSS variables:

```python
TEAL = "#21808D"   TEAL_LIGHT = "#32B8C6"   ORANGE = "#E68161"   RED = "#C0152F"
GREEN = "#21808D"  # teal = positive to match brand
BLUE = "#0567C8"   PURPLE = "#7C3AED"       GOLD = "#D97706"     NAVY = "#1A3756"
```

🔴 **Three parallel, non-matching palettes.** Chart teal is `#21808D`, CSS teal is `#0891B2`, dead-stylesheet teal is
`#00D4C8` — and `utils.py` defaults to `#00D4C8`. Only `PURPLE` (`#7C3AED`) matches across the Python and CSS sets.
`GREEN` is aliased to teal, so a "positive" chart series and a neutral brand element render identically.

### 6b. Typography

Loaded via two `@import url(...)` calls to Google Fonts (`app.py:182` and `app.py:731`) — **network-dependent**, and
the second import appears mid-stylesheet where `@import` is invalid per CSS spec (it must precede all rules).
**[INFERRED]** it works because browsers are lenient, but it is fragile.

Families: **Inter** (body/UI), **Syne** (display/headers), **Outfit**, **DM Sans**, **JetBrains Mono** (numerics).

Scale (live light theme, `app.py:763+`): base `14px`; markdown body `14px` / line-height `1.6`;
`stMetricValue` `2.2rem`; `stMetricLabel` `14px`; `stMetricDelta` `13px`; tab labels `15px` weight `600`;
sidebar `14px`; captions `13px`. Global smoothing: `-webkit-font-smoothing: antialiased`,
`-moz-osx-font-smoothing: grayscale`, `text-rendering: optimizeLegibility`.

*(The dead `styles.css` sets base `15px` — another divergence if it were ever wired up.)*

### 6c. Spacing

No spacing scale. Padding/margin are per-rule literals. Radii are the only consistently tokenized dimension
(`--dp-radius: 8px`, `--dp-radius-lg: 12px`).

### 6d. Breakpoints

**13 `@media` queries**, informally at `1024px` / `768px` / `480px`, plus **three separate `@media print`** blocks
(`app.py:3026`, `3357`, `7151`, `9241`) supporting the board-report export. There is no shared breakpoint definition
— each query restates its own pixel value.

### 6e. Theming

**There is no theme switch.** The light palette is hardcoded into the inline `:root`. `.streamlit/config.toml` sets
Streamlit's own theme. `assets/styles.css` (dark) and `assets/styles-light.css` are **both dead** — neither is read by
`app.py`, which never references the `assets/` directory at all.

The app also fights Streamlit's runtime layout with a documented three-part hack: a `<style>` injected into `<head>`
at runtime, a `requestAnimationFrame` loop for 5 s forcing `padding-top: 0px !important` inline, and a
`MutationObserver` watchdog on `document.documentElement`. Necessary because Streamlit's React sets `paddingTop`
inline *after* stylesheets load.

### 6f. Verdict: **ad hoc, not a system**

- 17 `<style>` blocks and **443 `unsafe_allow_html=True`** call sites in one file.
- Three conflicting color palettes; a fourth set of defaults in `utils.py`.
- Two full stylesheets committed but never loaded.
- `components_group._dark_fig()` renders dark charts on a white page — the exact anti-pattern `CLAUDE.md` warns about.
- `components.py` widgets render in **iframes**, so they are hard-isolated from every token above and duplicate their
  styling internally.
- Two `style_fig` implementations with different default heights (§3c).

**[INFERRED]** the design started dark (`styles.css` v5 "Deep Coastal Dark"), was converted to light inline in
`app.py`, and the old stylesheets plus dark-token defaults in `utils.py` and `components_group.py` were never cleaned
up. Consolidating to one token source is the highest-value visual cleanup.

---

## 7. Known gaps

### 🔴 Security

1. **Committed credentials.** `.env\r` (trailing CR) is **tracked in git** and holds `STR_USERNAME` / `STR_PASSWORD`.
   `.gitignore` contains `.env`, which does not match `.env\r`. Values are withheld here.
   **Action: rotate the STR credentials, `git rm --cached`, scrub history, and add `.env*` to `.gitignore`.**
2. `strategy_goals.compute_query` stores raw SQL that `compute_strategy_progress.py` executes. Safe while goals are
   admin-seeded; an injection vector the moment the goal editor (`app.py:10829+`) writes to it.
3. Admin gating is `st.query_params.get("admin","").lower() == "true"` — a **URL parameter, not authentication**.
   Anyone who knows the string gets Pipeline Controls and the API-key field. `_LOGIN_ENABLED = False` means there is
   no auth layer at all.

### 🔴 Correctness

4. **Dead `revpar_best_month` / `revpar_best_val` block** with a latent `NameError` (§5b, `app.py:5613–5619`).
5. **`tbid_ytd` vs `tbid_ytd_prior` are not like-for-like** — prior year is day-of-year capped, current year is not
   (§5b). Produces a structurally wrong YoY.
6. **Compression threshold defined four ways** — `>=` vs `>`, plus an undocumented 70% tier (§5c).
7. **Three `OCC_*` constants defined and never used** (§5c).
8. **Data is ~4 months stale** while the UI labels it current (§4e).
9. **`fact_str_metrics.market` is `'Anaheim Area'`** for every row, directly contradicting the bolded rule in
   `CLAUDE.md` (§4c).
10. **Leap-day YoY:** `date(as_of_date, '-1 year')` maps Feb 29 → Feb 28.
11. **`kpi_daily_summary` has 3 permanently-NULL legacy columns** (`occ_pct_yoy_pp`, `adr_yoy_pct`, `revpar_yoy_pct`).
12. **`components_group.render_group_tab` default `selected_model="claude"`** is not a valid `AI_MODELS` key
    (§3d) — the call site at `app.py:18562` passes a real value, so this only bites if the default is ever taken.

### 🟡 Null / empty-data handling

13. **`_sql()` swallows every exception and returns an empty DataFrame**, logging only at `DEBUG`. A typo, a schema
    drift, or a `TypeError` all present identically as "no data." The documented diagnosis path is to run the SQL
    directly:
    ```bash
    python3 -c "import sqlite3,pandas as pd; print(pd.read_sql_query('SELECT * FROM <table> LIMIT 1', sqlite3.connect('data/analytics.sqlite')))"
    ```
14. **139 `except Exception` blocks and 1 bare `except:` in `app.py`.** Most log to `_logger.debug`, which is not
    emitted at default log level, so failures are invisible in production.
15. **Single-row tables** (`datafy_overview_kpis`, `datafy_attribution_website_kpis`, `zartico_lodging_kpis`,
    `zartico_event_impact`, `datafy_social_ga_overview`, and others) are consumed via `.iloc[0]` — an empty frame
    raises `IndexError` inside a section, and `_safe_section()` then blanks the whole panel.
16. **All-NULL columns bind silently to empty charts**: `datafy_overview_dma.avg_length_of_stay_days` and
    `.trips_share_pct`.
17. **Empty tables that exist**: `events_insights` (0), `airbnb_market_data` (0).
18. **YoY is NULL for 366 of 760 `kpi_daily_summary` rows** (no prior-year date). Anything averaging the YoY columns
    must handle NaN — the first ~12 months of the series have none.
19. `empty_state(icon, title, body)` exists as a helper but is **not** applied uniformly; many sections simply render
    nothing when their frame is empty.

### 🟡 Dead code and repo hygiene

20. **Seven committed junk virtualenvs** at repo root: `already/`, `created/`, `if/`, `not/`, `skip/`, `you/`, `#/`.
    They dominate the **4,322 tracked files**.
21. **Dead files, all committed:** `dashboard/app.py.save` (192 KB), `dashboard/vdp-dashboard-v2.html` (68 KB),
    `dashboard/assets/styles.css` (558 lines), `dashboard/assets/styles-light.css` (284 lines),
    `scripts/load_str_monthly_sqlite_broken.py`, `scripts/load_str_monthly_sqlite.py.save`,
    `scripts/load_str_monthly_sqlite.pyo`, `scripts/"load_str_monthly_sqlite.py\x18"` (control char in filename),
    `GlobalMktProfile_UnitedStates (1).zip` (1 MB), `diagnose_docstring.py`, `fix_docstring.py`.
22. **5 of 7 `components.py` widgets imported but never called** (~450 lines) (§3b).
23. **`sec_div` / `style_fig` duplicated** with divergent defaults (§3c).
24. **`_render_login_page()`** — ~100 lines of permanently disabled UI, plus its `streamlit-authenticator` dependency.
25. **`app.py` is 19,181 lines / 1.1 MB.** `CLAUDE.md`'s own rule says to extract components past ~18K lines; that
    threshold is passed. All six tab bodies are inline module-level code, which is why the file resists navigation.
26. **`xlrd` is unpinned** — the only dependency without a version constraint, and `xlrd` 2.x dropped `.xlsx`
    support, so a fresh install can break the STR loaders.

### 🟡 Fragile mechanisms

27. **Tab deep-linking depends on a 100 ms `setTimeout` then a synthetic `.click()`** (`app.py:10039`). Silently
    no-ops on a slow render.
28. **The top-spacing fix is a 5-second `requestAnimationFrame` loop plus a `MutationObserver`** — it fights
    Streamlit's React on every rerun.
29. **The splash screen's readiness check must measure `[data-testid="stMainBlockContainer"]`, never `#root`** —
    `#root` collapses to height 0 permanently because `.stApp` is `position:absolute`. Getting this wrong makes the
    app hang on its 12 s failsafe ("stuck on loading"). Documented in `CLAUDE.md` from a past incident.
30. 🔴 **Never call `.close()` on a `get_connection()` handle.** It is a shared `@st.cache_resource` connection; a
    `.close()` in one loader broke every subsequent rerun with
    `sqlite3.ProgrammingError: Cannot operate on a closed database` and took production down. `get_connection()` is
    now self-healing and `tests/test_connection_safety.py` guards it, but **do not reintroduce the pattern.**
    `with get_connection() as conn:` is safe (sqlite's `__exit__` commits, it does not close).
31. **Google Fonts `@import` is network-dependent**, and the second import sits mid-stylesheet where `@import` is
    spec-invalid (§6b).
32. **`fetch_vdp_events.py` does not truly scrape** — the VDP calendar is JS-rendered, so it seeds known events.
33. **`fetch_str_dropbox.py` / `str_playwright_automation.py` depend on the leaked STR credentials** and will break
    the moment those are rotated. Rotating is still the right call — just update the secret store at the same time.

### 🟢 Working well (do not "fix")

- Single cached, PRAGMA-tuned connection with self-healing (`get_connection()`).
- Hot-path indexes embedded in **both** `_init_db()` and `scripts/optimize_db.py`, so fresh cloud deploys are covered.
- Pipeline parallelism: contiguous `PARALLEL_SAFE` network steps run in a thread pool (`PIPELINE_MAX_WORKERS`,
  default 5) with lock-guarded logging; STR/KPI/insight steps stay strictly sequential.
- Bulk `executemany()` + one upfront key `SELECT` in the STR loaders (1 round-trip, not 2N).
- `insights_daily` UPSERT on `(as_of_date, audience, category)` — same-day re-runs are safe.
- Negative STR values preserved as `NULL` rather than floored to `0.0`.
- `clean_copy()` enforces the no-em-dash house style at the data-loading chokepoint.

---

## 8. Key source — **SKIPPED, with a map instead**

Per your note about length: `dashboard/app.py` is **19,181 lines / 1.1 MB** and `components_group.py` is
**2,312 lines / 108 KB**. Pasting them would make this file unusable. Below is a line-indexed map so you can request
exact ranges — say the word and any range comes back verbatim.

### `dashboard/app.py` (19,181 lines) — line index

| Lines | Contents |
|---|---|
| 1–52 | Module docstring, copyright, imports, `_logger`, imports from `components` / `utils` / `components_coastal` / `components_group` |
| 54–117 | `md_to_html`, `clean_copy`, `smart_summary`, `bold_key_data` |
| 119–160 | `load_dotenv`, AI SDK availability flags, `_ENV_*` key reads, `st.set_page_config`, `inject_shader_wallpaper()` |
| 164–265 | `_LOGIN_ENABLED = False`, `_render_login_page()` (dormant) |
| 270–283 | **Brand palette + `OCC_*` thresholds** (short, high-value) |
| 286–342 | `CLAUDE_MODEL`, `AI_MODELS` registry (8 models) |
| 343–~1000 | **`SYSTEM_PROMPT`** — full domain knowledge, TBID structure, schema for all tables, audience framing. Cache-pinned; must stay ≥2048 tokens |
| ~730–4300 | **All inline CSS** — 17 `<style>` blocks, `:root` light tokens at 734–761, media queries, splash/spacing hacks |
| 4321–4470 | `ROOT`, `DB_PATH`, `_init_db()` schema DDL |
| 4456–4556 | `_HOT_INDEXES`, `_ensure_indexes`, `_open_connection`, **`get_connection`**, `_READ_PRAGMAS`, `_apply_read_pragmas` |
| 4548–4556 | **`_sql()`** — the universal query wrapper (small, essential) |
| 4558–5518 | **~90 `@st.cache_data` loaders** — STR, CoStar, Datafy, Zartico, Later, Visit CA, US Travel, weather/marine/AQI/tides/surf, FRED/EIA/TSA/BLS/Census, events, `get_table_counts()` |
| 5520–5620 | **`pct_delta` + `build_metrics_context`** — every Python-side formula; contains the dead-code bug |
| 5625–5785 | AI prompt builders: `_base`, `_datafy_summary_for_prompt`, `_build_visitor_econ_prompt`, `build_prompt`, `build_custom_prompt` |
| 5786–5970 | `fetch_vdp_website_context`, local fallbacks when no API key is present |
| 5973–6154 | **AI router**: `stream_claude_response`, `_stream_openai_compat` (also serves Perplexity), `_stream_gemini`, **`stream_ai_response(prompt, model_key, keys)`** |
| 6155–6525 | SVG builders: `kpi_metric_svg`, `sparkline_svg`, `insight_icon_svg`, `event_icon_svg` |
| 6525–6660 | `kpi_card`, `insight_card`, `event_stat` |
| 6659–6941 | Chart renderers: occ heatmap, comp-set radar, ADR/gas scatter, DMA bubble map, feeder Sankey, booking pace, content funnel |
| 6942–7093 | **`style_fig`** — the Plotly theming chokepoint |
| 7094–7525 | `sec_div`, `generate_section_html`, `render_share_bar`, `render_kpi_ticker`, `render_painted_occ_heatmap` |
| 7526–7745 | `compute_overview_kpis`, `generate_ai_insights`, `empty_state`, `tab_intro`, `callout`, `chart_primer` |
| 7747–7994 | Insight formatting: `_INSIGHT_PREFIX`, `_INSIGHT_ICON`, `_humanize_metric_key`, `_format_metric_value`, `_parse_insight_headline`, `_insight_lead_and_action`, `_select_metric_chips`, **`render_smart_insight_card`** |
| 7995–8047 | **`_safe_section`**, `_sh`, `source_card`, `grain_badge` |
| 8048–8230 | AI key resolution, `PLOTLY_CONFIG`, `_DAYS_MAP` |
| 8701–9814 | `_h_delta_html`, **`generate_board_report_html`** (~1,070 lines, print-optimized board export) |
| 9815–10057 | **`render_intel_panel`** — the AI Analyst UI |
| 10015–10052 | **Tab structure + JS deep-link injection** (short, high-value) |
| 10058–10110 | `_tab_controls`, `_str_filters` |
| 10111–19181 | **All six tab bodies, inline at module level.** Overview sub-tabs @10539 · Goals editor @10829 · AI chat @10907 · Hotel Trends @11070 · Comp-set sub-tabs @11885 · Forward Outlook audience tabs @12398 · Visitors sub-tabs @12845 · Events calendar @15631 · Market Intel sub-tabs @16147 · coastal call @18551 · group call @18562 · `_GLOSSARY_TERMS` @19070 · `_SOURCES_HTML` @19088 |

### Suggested reading order for a new instance

If you only read four things, read these — together they are ~1,000 lines and explain most of the app:

1. **`app.py:4321–4620`** — DB connection, PRAGMAs, indexes, `_sql`, and the first loaders. Explains why panels go
   blank.
2. **`app.py:5520–5620`** — every Python-side formula, plus the dead-code bug in §5b.
3. **`dashboard/utils.py`** (569 lines, whole file) — the formatting vocabulary the rest of the app speaks.
4. **`scripts/compute_kpis.py`** (~250 lines, whole file) — the canonical KPI SQL and the `>=` vs `>` inconsistency.

Then, by task: charts → `app.py:6659–7093`; AI → `app.py:5625–6154`; group tab → `components_group.py`;
board export → `app.py:8745–9814`.

### Files small enough to paste on request in full

`dashboard/utils.py` (569) · `dashboard/components_coastal.py` (339) · `dashboard/components.py` (709) ·
`scripts/compute_kpis.py` (~250) · `scripts/run_pipeline.py` · any of the four test files · `.streamlit/config.toml` ·
`requirements.txt`.

---

## Appendix — Pipeline reference

`scripts/run_pipeline.py` defines a **49-entry `STEPS` list** of `(name, script_path, fatal)` tuples. Contiguous runs
of steps listed in `PARALLEL_SAFE` execute in a thread pool (`PIPELINE_MAX_WORKERS`, default 5); everything else runs
sequentially. Each step logs `OK`/`SKIP`/`WARN`/`FAIL` with a timestamp to `logs/pipeline.log`.

**Fatal steps (abort the run):** `load_str_daily`, `load_str_monthly`, `compute_kpis`, `compute_insights`.
Every other step is non-fatal and logs a warning on failure.

**Ordering guarantees that matter:** `compute_kpis` must follow the STR loaders; `compute_insights` must follow
`compute_kpis` and every source loader (it reads all tables); `optimize_db` and `build_relationships` run last, with
`build_table_relationships.py` rebuilding all ~329 relationships from its `RELATIONSHIPS` registry — **add an entry
there whenever you add a table.**

**Commands:**
```bash
source venv/bin/activate
streamlit run dashboard/app.py                          # run the dashboard
python scripts/run_pipeline.py                          # full refresh
python scripts/build_table_relationships.py             # relationships only
pytest                                                  # test suite
```

**Deployment note from `CLAUDE.md`:** the owner requires commits **directly to `main`** (Streamlit Cloud auto-deploys
from it). This briefing was produced on a feature branch per the session's branch policy — reconcile the two before
merging.

---

*Prepared from a read-only pass over the repository at commit HEAD on branch `claude/dashboard-handoff-briefing-gkqbuw`.
No source files were modified. All figures in sample rows are dummy values; no credentials, tokens, or real
proprietary figures appear in this document.*
