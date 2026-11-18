# ERCOT Interconnection Queue: "What Changed" Feed

A data pipeline that scrapes ERCOT's monthly Generator Interconnection Status (GIS) reports, loads nearly five years of them into Postgres, and produces a monthly report of **what changed** in the queue: new projects, removed projects (and why), and changes to projected dates, study status and capacity.

Grid Status already shows the queue as it stands today. This project focuses on the question traders and developers ask next: *what changed since last month?*

**Sample output:** [`reports/2026-10.md`](reports/2026-10.md)

---

## What it found (October 2026 vs. September 2026)

| Change | Projects |
| --- | --- |
| New projects | 43 |
| Removed projects | 65 (53 cancelled, 8 commissioned, 2 inactive, 2 unexplained) |
| Projected date changed | 121 (117 pushed later, 4 moved earlier) |
| Study status changed | 53 |
| Capacity changed | 35 |

Across the full history (Feb 2022 – Oct 2026), the Large Generator queue grew from 788 projects to a peak of 1,881 in July 2025, and has shrunk since. Removals have regularly outnumbered additions since late 2025.

---

## How to run it

**Requirements:** [uv](https://docs.astral.sh/uv/) and [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# 1. Start Postgres (runs in Docker)
docker compose up -d

# 2. Install dependencies
uv sync

# 3. Download GIS reports from ERCOT (~100 files, a few minutes; already-downloaded files are skipped)
uv run python list_reports.py

# 4. Parse, validate and load reports into Postgres
uv run python db.py

# 5. Detect month-over-month changes
uv run python changes.py

# 6. Write the latest month's report to reports/YYYY-MM.md
uv run python report.py
```

Every step is safe to re-run.

**Tests and code checks:**

```bash
docker compose exec db createdb -U queue queue_test   # one time: separate test database
uv run pytest
uv run ruff check .
```

---

## How it works

```
ERCOT JSON feed → download → parse → validate ─┬─→ Postgres → change detection → Markdown report
                                               └─→ quarantine (with reason)
```

| File | Job |
| --- | --- |
| `list_reports.py` | Lists GIS reports from ERCOT's JSON feed and downloads new ones (with retries and polite pauses) |
| `parse.py` | Turns a spreadsheet into a clean table, reads the cancellation/inactive/commissioning sheets, and validates the result |
| `db.py` | Creates the tables and loads each report in a single transaction; quarantines files that fail |
| `changes.py` | Compares each month with the previous one and stores every change in `change_events` |
| `report.py` | Builds the Markdown report for the latest month |
| `tests/` | 14 tests for parsing, validation, report formatting and change detection |

### Tables

| Table | One row per |
| --- | --- |
| `files` | loaded report |
| `projects` | project **per report**, so every month is kept as a snapshot, which is what makes comparisons possible |
| `project_events` | project ERCOT lists as cancelled, inactive or commissioned in a report |
| `change_events` | change detected between two consecutive reports |
| `quarantine` | file that failed parsing or validation, with the reason |

---

## How it handles real-world data problems

| Problem found in ERCOT's data | How the pipeline handles it | Tested |
| --- | --- | --- |
| Report links aren't in the page HTML (loaded by JavaScript) | Calls the JSON feed the page uses directly, instead of automating a browser | |
| The header row is on different rows in different sheets | Searches every column for the `INR` header | ✅ |
| Older reports use a different sheet name and column name | Tries known sheet names in order; renames old columns via an alias map | ✅ |
| A column goes missing | Fails with a clear "Missing columns" error → quarantine | ✅ |
| "No cancelled projects during the month" instead of a table | Treated as zero events; any *other* unexpected layout still fails | ✅ |
| Text in a numeric column, duplicate IDs, nearly empty sheet | Caught by `validate()` → quarantine | ✅ |
| ERCOT publishes corrected reports a few days later | A file published within 15 days of the previous one replaces it in comparisons | |
| Stray spaces in text (`"Priddy Wind "`) | Stripped, so they don't appear as fake changes | |
| Same file loaded twice / run interrupted | Already-loaded files are skipped; each file loads in one transaction | ✅ |
| Projects disappearing without explanation | Labelled using ERCOT's event sheets, or flagged `unexplained` | ✅ |

**Reconciliation check:** for each month, previous total − removed + added = current total. This matched exactly in every month I checked by hand.

---

## Key decisions and alternatives

- **Call ERCOT's JSON feed rather than scrape HTML or use Selenium.** Simpler, faster, and less fragile than browser automation.
- **Postgres in Docker rather than SQLite.** Matches Grid Status's stack, and gives real `DATE` and exact `NUMERIC` types. `NUMERIC` for capacity avoids fake changes from floating-point rounding. Docker means a reviewer gets the same database with one command.
- **Keep a full snapshot per month** (`projects` keyed by report + project) rather than only the latest state. It costs more rows (~87k), but makes any two months comparable and the change detection simple SQL.
- **Store change old/new values as text** so one table fits dates, statuses and numbers. Trade-off: no date math directly on those columns.
- **Rebuild `change_events` from scratch on every run.** It's fully derived from `projects`, so rebuilding is always correct and a late correction can't leave stale results.
- **`IS DISTINCT FROM` instead of `<>`** so changes to or from an empty value (`NULL`) aren't silently missed.
- **Quarantine instead of crash.** The main loop deliberately catches any exception (marked with a `noqa` and a comment) so one bad file doesn't stop the run.
- **Per-type report columns.** "Old/New" makes no sense for a new or removed project, so each section shows only the columns that fit.

More detail, including dead ends, is in [`DECISIONS.md`](DECISIONS.md).

---

## Scope

- **Reports from February 2022 onward** (57 monthly reports plus 2 corrections, 56 comparisons). Older reports use a different layout; I added support for their sheet and column names, but some store dates as text, six were re-published on the same day (so publish date can't order them), and there are gaps. Supporting them properly needs ordering by the report month parsed from inconsistent file names. Those files are skipped and logged as out of scope.
- **Large Generator projects only.** Small Generator projects are on a separate sheet and not loaded yet.

## Scraping etiquette

The scraper identifies itself with a descriptive User-Agent, pauses 2 seconds between downloads, retries with increasing waits rather than hammering the server, and never re-downloads files it already has.

---

## How I used AI

<!-- Edit this section in your own words. -->

I used Claude as a tutor and pair programmer throughout. It drafted most of the code, and I ran, debugged and questioned every piece until I could explain it. The investigation and the decisions were mine: finding the JSON feed with the browser's Network tab, choosing Postgres, using ERCOT's event sheets to explain removals, scoping to February 2022 after the backfill exposed the older formats, and tailoring the report's columns per change type. Debugging real issues (Excel lock files, an empty events table caused by my own skip-if-loaded logic, the 2023 "no cancellations" files) taught me the most.

---

## Not production-ready yet / what I'd do next

- **Scheduling and alerting:** runs are manual. Next: a monthly scheduled job, plus an alert when a file is quarantined or a month has unusual counts.
- **Older reports:** order by report month parsed from file names, convert text dates, then lift the Feb 2022 cutoff.
- **Small Generator projects** from their own sheet.
- **Better labels:** most batteries are coded as fuel `OTH`; use the `technology` column to label them. Split the combined study-status text into separate SS / FIS / IA milestones.
- **Noise thresholds:** decide whether tiny capacity changes (e.g. under 1 MW) belong in the feed.
- **Stale dates:** flag projects whose projected date is already in the past.
- **Credentials:** the database password is a local-only default; in production it would come from a secrets manager.
- **CI:** run Ruff and pytest on every push with GitHub Actions.
- **Investigate the 2 unexplained October removals** (Hector Solar, Sendero Solar).
