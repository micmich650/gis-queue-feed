# ERCOT Interconnection Queue: What Changed Each Month

This project downloads ERCOT's monthly Generator Interconnection Status (GIS) reports, loads them into Postgres, and compares each month with the one before. The output is a monthly report showing which projects were added or removed (and why), and which had their projected date, study status or capacity change.

Sample report: [`reports/2026-10.md`](reports/2026-10.md)

## What it found

Comparing October 2026 with September 2026:

- 43 new projects
- 65 removed: 53 cancelled, 8 commissioned, 2 inactive, 2 with no reason given
- 121 projected dates changed, 117 of them pushed later
- 53 study status changes
- 35 capacity changes

Over the full history I loaded (Feb 2022 to Oct 2026), the queue grew from 788 projects to a peak of 1,881 in July 2025 and has been shrinking since.

## How to run it

You'll need [uv](https://docs.astral.sh/uv/) and [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
docker compose up -d                 # start Postgres
uv sync                              # install dependencies
uv run python list_reports.py        # download the reports (takes a few minutes)
uv run python db.py                  # parse, validate and load them
uv run python changes.py             # find month-over-month changes
uv run python report.py              # write reports/YYYY-MM.md
```

Each step can be run again safely.

To run the tests:

```bash
docker compose exec db createdb -U queue queue_test   # only needed once
uv run pytest
uv run ruff check .
```

## How it works

| File | What it does |
| --- | --- |
| `list_reports.py` | Gets the list of GIS reports from ERCOT and downloads any new ones |
| `parse.py` | Reads a report into a clean table and checks it looks right |
| `db.py` | Loads each report into Postgres, or quarantines it if something's wrong |
| `changes.py` | Compares each month with the previous one and saves the differences |
| `report.py` | Writes the report for the latest month |

I keep a full copy of every month's projects in the database rather than just the latest version, which is what makes it possible to compare any two months.

## Problems I ran into

- The report links on ERCOT's page aren't in the HTML. They're loaded with JavaScript, so I used the browser's Network tab to find the JSON feed the page calls and used that directly.
- The header row isn't in the same place in every sheet, so the parser searches for the `INR` column instead of assuming a row number.
- Some months have no cancellations, and the sheet just has a note saying so instead of a table. The parser treats that as zero events but still fails on any other unexpected layout.
- ERCOT sometimes publishes a corrected report a few days after the original. If a file comes out within 15 days of the previous one, I use it in place of the original.
- Files that fail any check are saved to a quarantine table with the reason, so one bad file doesn't stop the run.

To check the change detection, I made sure the counts add up: last month's total, minus removed, plus added, equals this month's total. It matched for the months I checked by hand.

More detail on the decisions I made and why is in [`DECISIONS.md`](DECISIONS.md).

## Scope

- Only reports from February 2022 onward. Older reports use a different layout, store some dates as text, and several were re-published on the same day, so I couldn't reliably put them in order. Those files are skipped.
- Only Large Generator projects. Small Generator projects are on a separate sheet I haven't loaded yet.
