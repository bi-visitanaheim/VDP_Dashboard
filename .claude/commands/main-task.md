# Main Task — Full Platform Refresh

Run this to do everything: fetch new data, rebuild all relationships, generate fresh insights, and push to main.

## Rules (read before doing anything)

- **Never add a new data source without asking first.** If a fetch script discovers a new API or file type that wasn't previously wired in, stop and ask: "Found potential new source: [name]. Add it? Yes/No."
- **Skip data that hasn't changed.** Check the `load_log` table for each source. If the most recent `run_at` for a source is today's date and rows were inserted, log "SKIP [source] — already refreshed today" and continue. Do NOT re-run that source's loader.
- **Always run `compute_insights.py` even if no new data.** New insights should always be generated fresh regardless of data age. This is never skipped.
- **Report data freshness.** After each step, note whether data was new, skipped (up to date), or stale (old data, no update available).

## Steps

### 1. Pull latest code
```bash
git pull origin main
```

### 2. Check what data is already fresh today
```python
python3 -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/analytics.sqlite')
df = pd.read_sql_query('''
    SELECT source, MAX(run_at) as last_run, SUM(rows_inserted) as total_rows
    FROM load_log
    WHERE run_at >= date(\"now\")
    GROUP BY source
    ORDER BY last_run DESC
''', conn)
print(df.to_string())
conn.close()
"
```
Use this to know which sources have already been refreshed today and can be skipped.

### 3. Run the full pipeline
```bash
python3 scripts/run_pipeline.py
```

The pipeline auto-handles:
- STR daily + monthly data (Steps 1–2)
- Datafy visitor economy (Step 3)
- KPI computation (Step 4)
- Insights generation — ALWAYS runs (Step 5)
- CoStar, Visit California, Zartico, Later.com social (Steps 6–10)
- External signals: FRED, EIA gas, TSA, BLS, NOAA, weather, Wikipedia, etc. (Steps 11–20)
- Table relationships rebuild — always last (Step 20)

### 4. Check for new potential data sources
After the pipeline runs, review the pipeline log for any new data sources mentioned in WARN messages that could be worth adding. For each candidate:
- Ask the user: "Found potential new source: [name/description]. Should I add it? (Yes/No)"
- Only proceed if the user says yes
- If yes, follow the Standard Process from CLAUDE.md: raw files → loader → relationships → pipeline step → dashboard → commit

### 5. Check data freshness report
```bash
python3 -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/analytics.sqlite')
# Show what's fresh vs stale
tables = ['fact_str_metrics', 'kpi_daily_summary', 'insights_daily', 'datafy_overview_kpis',
          'costar_market_snapshot', 'later_ig_profile_growth', 'zartico_kpis']
for t in tables:
    try:
        row = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()
        print(f'{t}: {row[0]} rows')
    except:
        print(f'{t}: not found')

# STR freshness
fresh = conn.execute(\"SELECT MAX(as_of_date) FROM fact_str_metrics\").fetchone()[0]
print(f'STR data last date: {fresh}')

# Insights freshness
ins = conn.execute(\"SELECT audience, COUNT(*), MAX(as_of_date) FROM insights_daily GROUP BY audience\").fetchall()
print('Insights:')
for r in ins: print(f'  {r}')
conn.close()
"
```

### 6. Run app audit
```bash
python3 scripts/audit_app.py
```
Review warnings. Flag anything that needs attention to the user.

### 7. Commit and push to main
```bash
git add data/analytics.sqlite scripts/compute_insights.py dashboard/app.py
git add -u
git status
```

Then commit with a message that includes:
- Date of refresh
- Row counts for key tables
- Number of insights generated
- Any new data sources added

```bash
git commit -m "Pipeline refresh $(date +%Y-%m-%d): [N] insights, [N] table relationships, [sources updated]"
git push -u origin main
```

## What to report when done

At the end, report:
1. **Data freshness** — for each major source, was data new or already current?
2. **Insights** — how many generated, for which audiences, any new categories?
3. **Table relationships** — total count
4. **New data sources** — any candidates found? Did user approve?
5. **Warnings** — any ⚠️ or ❌ from the audit that need attention
6. **STR data age** — last STR data date (flag if >30 days old — user needs to drop new STR exports)

## Skipping stale sources (smart logic)

Before re-running any external fetch:
- Check `load_log` for today's entries for that source
- If source was already loaded today with rows > 0: log "SKIP" and move on
- If source has never been loaded OR last loaded >7 days ago: run it and note as "refreshed"
- If source shows 0 rows consistently: note as "no data available" and skip

This prevents redundant API calls and speeds up the refresh cycle.
