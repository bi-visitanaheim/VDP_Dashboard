"""
load_vdp_intelligence_context.py
─────────────────────────────────
Seeds six reference tables that power the Visit Dana Point Intelligence
Assistant panel and provide structured context for the AI Analyst.

Tables created / refreshed:
  vdp_org_facts             — key organizational / destination facts
  vdp_strategic_concerns    — 8 strategic concern areas
  vdp_ai_skills             — Claude AI skills catalog (9 skills)
  vdp_ai_starter_questions  — quick-launch UI questions (8 items)
  vdp_mcp_integrations      — recommended MCP server connections (5)
  vdp_city_strategic_metrics — FY26 city strategic plan KPIs

All tables use a full DELETE + INSERT pattern (idempotent re-runs).
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH      = os.path.join(PROJECT_ROOT, "data", "analytics.sqlite")
NOW          = datetime.utcnow().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# DDL
# ─────────────────────────────────────────────────────────────────────────────

SCHEMAS: dict[str, str] = {
    "vdp_org_facts": """
        CREATE TABLE IF NOT EXISTS vdp_org_facts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            category         TEXT NOT NULL,
            fact_name        TEXT NOT NULL,
            fact_value_text  TEXT,
            fact_value_num   REAL,
            fact_unit        TEXT,
            source           TEXT,
            as_of_year       INTEGER,
            loaded_at        TEXT DEFAULT (datetime('now'))
        );
    """,
    "vdp_strategic_concerns": """
        CREATE TABLE IF NOT EXISTS vdp_strategic_concerns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            concern_number  INTEGER NOT NULL,
            concern_name    TEXT NOT NULL,
            concern_slug    TEXT NOT NULL,
            summary         TEXT,
            key_data_points TEXT,
            priority_rank   INTEGER,
            loaded_at       TEXT DEFAULT (datetime('now'))
        );
    """,
    "vdp_ai_skills": """
        CREATE TABLE IF NOT EXISTS vdp_ai_skills (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name          TEXT NOT NULL,
            trigger_description TEXT,
            description         TEXT,
            behavior_summary    TEXT,
            output_format       TEXT,
            loaded_at           TEXT DEFAULT (datetime('now'))
        );
    """,
    "vdp_ai_starter_questions": """
        CREATE TABLE IF NOT EXISTS vdp_ai_starter_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            category      TEXT,
            emoji         TEXT,
            display_order INTEGER,
            loaded_at     TEXT DEFAULT (datetime('now'))
        );
    """,
    "vdp_mcp_integrations": """
        CREATE TABLE IF NOT EXISTS vdp_mcp_integrations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name   TEXT NOT NULL,
            data_source   TEXT,
            use_case      TEXT,
            priority_rank INTEGER,
            loaded_at     TEXT DEFAULT (datetime('now'))
        );
    """,
    "vdp_city_strategic_metrics": """
        CREATE TABLE IF NOT EXISTS vdp_city_strategic_metrics (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_period     TEXT NOT NULL,
            goal_number       INTEGER,
            goal_name         TEXT,
            metric_name       TEXT NOT NULL,
            metric_value_num  REAL,
            metric_value_text TEXT,
            metric_unit       TEXT,
            source            TEXT,
            loaded_at         TEXT DEFAULT (datetime('now'))
        );
    """,
}


# ─────────────────────────────────────────────────────────────────────────────
# Seed data
# ─────────────────────────────────────────────────────────────────────────────

ORG_FACTS = [
    # category, fact_name, fact_value_text, fact_value_num, fact_unit, source, as_of_year
    ("TBID",     "annual_marketing_budget",    "$1.7M",    1_700_000.0,  "USD",           "Civitas Advisors / Visit Dana Point",    2024),
    ("TBID",     "district_rate_current",      "9.4%",          9.4,    "percent",        "TBID conversion 2019",                   2019),
    ("TBID",     "district_rate_previous",     "8.9%",          8.9,    "percent",        "TBID pre-2019",                          2019),
    ("TBID",     "blended_assessment_rate",    "~1.25%",        1.25,   "percent",        "CLAUDE.md formula",                      2024),
    ("TBID",     "tot_rate",                   "10%",          10.0,    "percent",        "City of Dana Point",                     2024),
    ("Harbor",   "revitalization_total_cost",  "$600M",   600_000_000.0, "USD",           "Dana Point Harbor Revitalization",       2024),
    ("Harbor",   "commercial_core_reopened",   "July 2025",     None,   "date",           "danapointharbor.com",                    2025),
    ("Harbor",   "phase_1_start",              "Feb 7 2024",    None,   "date",           "danapointharbor.com",                    2024),
    ("Harbor",   "phase_2_start",              "July 2024",     None,   "date",           "danapointharbor.com",                    2024),
    ("Regional", "oc_visitor_spending_2024",   "$1.32B",  1_320_000_000.0, "USD",         "OC Tourism Director / CitizenPortal",    2024),
    ("Regional", "oc_visitor_spending_yoy",    "+4%",           4.0,   "percent_yoy",    "OC Tourism Director / CitizenPortal",    2024),
    ("Events",   "ohana_festival_attendance",  "86,100",    86_100.0, "attendees",       "City FY26 Strategic Plan",               2025),
    ("Events",   "boat_parade_attendance",     "25,400",    25_400.0, "attendees",       "City FY26 Strategic Plan",               2025),
    ("Events",   "turkey_trot_attendance",     "12,500",    12_500.0, "attendees",       "City FY26 Strategic Plan",               2025),
    ("STR",      "unpermitted_strs_h1_fy26",   "58",            58.0, "properties",      "City FY26 Mid-Year Strategic Plan",      2025),
    ("Transport","trolley_saturday_riders_min","308",          308.0, "weekly_riders",   "City FY26 Mid-Year Strategic Plan",      2025),
    ("Transport","trolley_saturday_riders_max","621",          621.0, "weekly_riders",   "City FY26 Mid-Year Strategic Plan",      2025),
    ("Partners", "city_chamber_collaborations","7",              7.0, "collaborations",  "City FY26 Mid-Year Strategic Plan H1",   2025),
    ("Partners", "business_retention_visits",  "322",          322.0, "visits",          "City FY26 Mid-Year Strategic Plan H1",   2025),
    ("Partners", "capital_investments_local",  "$1.5M",  1_500_000.0, "USD",            "City FY26 Mid-Year Strategic Plan H1",   2025),
    ("Datafy",   "ohana_event_expenditure",    "$14.6M", 14_600_000.0, "USD",            "Datafy event report",                    2024),
    ("Datafy",   "ohana_destination_spend",    "$18.4M", 18_400_000.0, "USD",            "Datafy event report",                    2024),
    ("Datafy",   "ohana_adr_lift",             "$139",         139.0, "USD",             "Datafy event report",                    2024),
    ("Datafy",   "ohana_spend_multiplier",     "3.2x",           3.2, "multiplier",      "Datafy event report",                    2024),
    ("Datafy",   "ohana_out_of_state_pct",     "68%",           68.0, "percent",         "Datafy event report",                    2024),
]

STRATEGIC_CONCERNS = [
    # concern_number, concern_name, concern_slug, summary, key_data_points, priority_rank
    (1, "TBID Funding & Budget Constraints",
     "tbid_funding",
     "VDP operates a $1.7M annual TBID budget. Demonstrating ROI and maximizing budget efficiency are ongoing priorities. District converted from 8.9% to 9.4% in 2019 to expand contributor base.",
     "Budget: $1.7M | Rate: 9.4% | Blended TBID: ~1.25% | TOT: 10%",
     1),
    (2, "Harbor Revitalization Disruption",
     "harbor_revitalization",
     "$600M harbor revitalization underway. Commercial core phases reopened July 2025. Construction disrupted visitor experience, boater access, and local business. Community concerns about gentrification persist.",
     "Cost: $600M | Commercial core reopened: July 2025 | Phase 1: Feb 2024 | Phase 2: July 2024",
     2),
    (3, "Visitor Data Gaps & Analytics",
     "visitor_data_gaps",
     "VDP faces challenges obtaining real-time, granular visitor data — origin markets, dwell time, spending, sentiment. OC visitor spending $1.32B in 2024 (+4% YOY), but hyper-local Dana Point data remains difficult to isolate.",
     "OC spending: $1.32B (2024) | YOY: +4% | Data platforms: Arrivalist, Zartico, Placer.ai, STR",
     3),
    (4, "Destination Positioning & Competitive Identity",
     "destination_positioning",
     "Historically positioned around four luxury resorts. Current focus broadens appeal to surfers, whale watching, group meetings, leisure families. Must differentiate from Laguna Beach, Newport Beach, San Clemente.",
     "Segments: luxury, active outdoor, family, group meetings, marine | Competitors: Laguna Beach, Newport Beach, San Clemente",
     4),
    (5, "STR Compliance & Monitoring",
     "str_compliance",
     "City tracks unpermitted STRs and citations. 58 unpermitted STRs identified in H1 FY26. STR activity affects hotel occupancy, TBID revenue, and neighborhood quality.",
     "Unpermitted STRs (H1 FY26): 58 | Platforms: Airbnb, VRBO | Impact: hotel occ, TBID revenue, community",
     5),
    (6, "Community Sentiment & Resident Relations",
     "community_sentiment",
     "City strategic plan prioritizes unique sense of place. Major events (Ohana 86,100 attendees, Boat Parade 25,400, Turkey Trot 12,500) are central to community identity. Balancing resident quality of life with visitor growth is ongoing.",
     "Ohana: 86,100 | Boat Parade: 25,400 | Turkey Trot: 12,500 | City goal: maintain unique sense of place",
     6),
    (7, "Trolley, Transportation & Accessibility",
     "transportation_access",
     "Trolley ridership tracked in city metrics (308-621 Saturday riders weekly). Multi-modal transportation is a strategic priority. VDP promotes sustainable visitor access.",
     "Saturday ridership: 308-621/week | Modes: trolley, PCH, multi-modal",
     7),
    (8, "Organizational Capacity & Partnership Development",
     "partnerships_capacity",
     "7 collaborations with Chamber and City in H1 FY26. 322 business retention visits. $1.5M capital investments in local businesses. Strengthening partnerships and communicating value are standing priorities.",
     "City/Chamber collabs: 7 | Business visits: 322 | Capital investments: $1.5M",
     8),
]

AI_SKILLS = [
    # skill_name, trigger_description, description, behavior_summary, output_format
    ("analyzing-tbid-data",
     "User asks about TBID revenue, budget, or ROI",
     "Interprets TBID assessment data, models budget scenarios, and frames marketing ROI for board presentations.",
     "Use blended 1.25% rate on room revenue. Cite STR ADR/RevPAR. Compare to $1.7M budget. Flag YOY changes >10%.",
     "Summary table of TBID metrics + 2-3 budget/ROI recommendations"),
    ("interpreting-str-metrics",
     "User asks about short-term rentals, Airbnb, VRBO, or lodging tax",
     "Reads STR occupancy/ADR/RevPAR data, maps enforcement data against revenue projections, surfaces compliance impact.",
     "Cross-reference fact_str_metrics with vdp_city_strategic_metrics STR data. Quantify TBID impact of unpermitted units.",
     "STR metrics table + enforcement impact + lodging tax revenue estimate"),
    ("drafting-board-reports",
     "User asks to draft, write, or summarize a board update",
     "Produces structured board-ready reports using Visit Dana Point's voice: concise, data-led, action-oriented.",
     "Lead with headline metric. Use AP style. No em dashes. Close with recommended board action.",
     "Structured report: Executive Summary | Key Metrics | Highlights | Recommended Actions"),
    ("writing-press-releases",
     "User asks to write a press release, announcement, or media pitch",
     "Generates AP-style press releases with standard lede, boilerplate, and contact block tailored to Dana Point's brand.",
     "AP style. No Oxford comma. Numerals for 10+. Include boilerplate: 'Visit Dana Point is...' Close with ###.",
     "FOR IMMEDIATE RELEASE | Lede | Body (3-4 graphs) | Boilerplate | Contact | ###"),
    ("analyzing-visitor-data",
     "User asks about visitor origin, dwell time, spending, or sentiment",
     "Interprets uploaded occupancy CSV, STR exports, or Arrivalist/Zartico data; flags anomalies and recommends follow-up.",
     "Note data source and date range. Flag YOY changes >10%. Recommend third-party data when gaps exist.",
     "| Metric | Value | YOY Change | Notes | + 2-3 actionable recommendations"),
    ("benchmarking-competitors",
     "User asks how Dana Point compares to Laguna Beach, Newport, or San Clemente",
     "Runs competitive framing across ADR, marketing budget, visitor segments, and event calendar.",
     "Use STR ADR/RevPAR as primary comparison. Highlight Dana Point differentiators: harbor, whale watching, surf heritage.",
     "Comparison table: Dana Point vs. competitors | Differentiation narrative | Positioning recommendation"),
    ("creating-social-content",
     "User asks for social media captions, content ideas, or campaign copy",
     "Generates platform-specific copy (Instagram, LinkedIn, Facebook) aligned to Dana Point's visual and tonal identity.",
     "Instagram: aspirational + hashtags. LinkedIn: professional + data. Facebook: community-warm. No em dashes.",
     "Platform-labeled copy blocks + 3 hashtag suggestions per platform"),
    ("summarizing-harbor-updates",
     "User asks about harbor construction, revitalization phases, or disruption messaging",
     "Delivers current-phase status, key milestone summaries, and stakeholder-ready talking points.",
     "Frame disruption as transformation. Lead with what IS open. Close with vision statement for completed harbor.",
     "Phase status table | Key milestones | 3 stakeholder talking points"),
    ("translating-city-data",
     "User references city strategic plan metrics, event attendance, trolley ridership, or code enforcement",
     "Cross-references FY26 strategic plan KPIs and translates city metrics into tourism-relevant insights.",
     "Pull from vdp_city_strategic_metrics. Connect city metrics to TBID revenue, visitor economy, and DMO narrative.",
     "City metric → Tourism implication table + DMO narrative recommendation"),
]

STARTER_QUESTIONS = [
    # question_text, category, emoji, display_order
    ("What are Dana Point's top visitor experience strengths and gaps?",           "positioning",   "🏖️", 1),
    ("Help me interpret our latest occupancy and ADR data.",                       "analytics",     "📊", 2),
    ("How should we communicate the harbor revitalization to group clients?",      "harbor",        "🏗️", 3),
    ("Draft a partner update on our FY26 marketing performance.",                  "communications","🤝", 4),
    ("What messaging resonates with active outdoor travelers visiting Dana Point?", "content",       "🌊", 5),
    ("Write a press release announcing a new hotel partner.",                      "pr",            "📢", 6),
    ("How do STR trends impact our TBID funding projections?",                     "tbid",          "🏡", 7),
    ("What does Visit California's Orange County regional plan say about Dana Point?", "regional",  "🗺️", 8),
]

MCP_INTEGRATIONS = [
    # server_name, data_source, use_case, priority_rank
    ("Google Drive MCP",    "Board agendas, strategic plans, reports",          "Claude reads and references internal documents without manual upload",    1),
    ("Google Sheets MCP",   "STR data exports, event attendance, lodging metrics","Claude queries live spreadsheet data in real time",                     2),
    ("GitHub MCP",          "App codebase, version history",                    "Maintains code context for ongoing development and debugging",            3),
    ("SQLite MCP",          "analytics.sqlite (occupancy, TBID, trolley)",      "Claude queries DB tables directly for real-time data-grounded answers",  4),
    ("Slack MCP",           "Team communications (optional)",                   "Surface relevant past conversations and draft channel updates",           5),
]

CITY_STRATEGIC_METRICS = [
    # fiscal_period, goal_number, goal_name, metric_name, metric_value_num, metric_value_text, metric_unit, source
    ("FY26-H1", 3, "Economic Health", "city_chamber_vdp_collaborations",    7.0,          "7",      "count",        "City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 3, "Economic Health", "business_retention_visits",         322.0,       "322",     "visits",       "City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 3, "Economic Health", "capital_investments_local_biz",     1_518_865.0, "$1,518,865","USD",        "City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 5, "Sense of Place",  "unpermitted_strs_identified",        58.0,         "58",     "properties",   "City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 5, "Sense of Place",  "trolley_saturday_riders_min",       308.0,        "308",     "weekly_riders","City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 5, "Sense of Place",  "trolley_saturday_riders_max",       621.0,        "621",     "weekly_riders","City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 5, "Sense of Place",  "ohana_festival_attendance",      86_100.0,     "86,100",    "attendees",    "City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 5, "Sense of Place",  "boat_parade_attendance",         25_400.0,     "25,400",    "attendees",    "City FY26 Mid-Year Strategic Plan"),
    ("FY26-H1", 5, "Sense of Place",  "turkey_trot_attendance",         12_500.0,     "12,500",    "attendees",    "City FY26 Mid-Year Strategic Plan"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def ensure_schemas(cur: sqlite3.Cursor) -> None:
    for ddl in SCHEMAS.values():
        cur.executescript(ddl)


def _truncate(cur: sqlite3.Cursor, table: str) -> None:
    cur.execute(f"DELETE FROM {table}")


def _insert_rows(cur: sqlite3.Cursor, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ",".join("?" * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    cur.executemany(sql, [list(r.values()) for r in rows])


# ─────────────────────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────────────────────

def load_org_facts(cur: sqlite3.Cursor) -> int:
    _truncate(cur, "vdp_org_facts")
    rows = [
        {
            "category":        r[0],
            "fact_name":       r[1],
            "fact_value_text": r[2],
            "fact_value_num":  r[3],
            "fact_unit":       r[4],
            "source":          r[5],
            "as_of_year":      r[6],
            "loaded_at":       NOW,
        }
        for r in ORG_FACTS
    ]
    _insert_rows(cur, "vdp_org_facts", rows)
    return len(rows)


def load_strategic_concerns(cur: sqlite3.Cursor) -> int:
    _truncate(cur, "vdp_strategic_concerns")
    rows = [
        {
            "concern_number":  r[0],
            "concern_name":    r[1],
            "concern_slug":    r[2],
            "summary":         r[3],
            "key_data_points": r[4],
            "priority_rank":   r[5],
            "loaded_at":       NOW,
        }
        for r in STRATEGIC_CONCERNS
    ]
    _insert_rows(cur, "vdp_strategic_concerns", rows)
    return len(rows)


def load_ai_skills(cur: sqlite3.Cursor) -> int:
    _truncate(cur, "vdp_ai_skills")
    rows = [
        {
            "skill_name":          r[0],
            "trigger_description": r[1],
            "description":         r[2],
            "behavior_summary":    r[3],
            "output_format":       r[4],
            "loaded_at":           NOW,
        }
        for r in AI_SKILLS
    ]
    _insert_rows(cur, "vdp_ai_skills", rows)
    return len(rows)


def load_starter_questions(cur: sqlite3.Cursor) -> int:
    _truncate(cur, "vdp_ai_starter_questions")
    rows = [
        {
            "question_text": r[0],
            "category":      r[1],
            "emoji":         r[2],
            "display_order": r[3],
            "loaded_at":     NOW,
        }
        for r in STARTER_QUESTIONS
    ]
    _insert_rows(cur, "vdp_ai_starter_questions", rows)
    return len(rows)


def load_mcp_integrations(cur: sqlite3.Cursor) -> int:
    _truncate(cur, "vdp_mcp_integrations")
    rows = [
        {
            "server_name":   r[0],
            "data_source":   r[1],
            "use_case":      r[2],
            "priority_rank": r[3],
            "loaded_at":     NOW,
        }
        for r in MCP_INTEGRATIONS
    ]
    _insert_rows(cur, "vdp_mcp_integrations", rows)
    return len(rows)


def load_city_strategic_metrics(cur: sqlite3.Cursor) -> int:
    _truncate(cur, "vdp_city_strategic_metrics")
    rows = [
        {
            "fiscal_period":     r[0],
            "goal_number":       r[1],
            "goal_name":         r[2],
            "metric_name":       r[3],
            "metric_value_num":  r[4],
            "metric_value_text": r[5],
            "metric_unit":       r[6],
            "source":            r[7],
            "loaded_at":         NOW,
        }
        for r in CITY_STRATEGIC_METRICS
    ]
    _insert_rows(cur, "vdp_city_strategic_metrics", rows)
    return len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] load_vdp_intelligence_context: starting …")

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cur  = conn.cursor()

    ensure_schemas(cur)
    conn.commit()

    totals: dict[str, int] = {}
    loaders = [
        ("vdp_org_facts",              load_org_facts),
        ("vdp_strategic_concerns",     load_strategic_concerns),
        ("vdp_ai_skills",              load_ai_skills),
        ("vdp_ai_starter_questions",   load_starter_questions),
        ("vdp_mcp_integrations",       load_mcp_integrations),
        ("vdp_city_strategic_metrics", load_city_strategic_metrics),
    ]
    for table, fn in loaders:
        n = fn(cur)
        totals[table] = n
        print(f"  {table}: {n} rows")

    total_rows = sum(totals.values())

    cur.execute(
        "INSERT INTO load_log (source, grain, file_name, rows_inserted, run_at) VALUES (?,?,?,?,?)",
        ("vdp_intelligence_context", "reference", "scripts/load_vdp_intelligence_context.py",
         total_rows, NOW),
    )
    conn.commit()
    conn.close()

    ts2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts2}] load_vdp_intelligence_context: {total_rows} total rows across {len(loaders)} tables — done.")


if __name__ == "__main__":
    main()
