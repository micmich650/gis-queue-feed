# Decisions

## Finding the data
- The GIS report page loads its file list with JavaScript, so the links
  aren't in the HTML. I found the JSON feed the page uses
  (reportTypeId=15933) and call it directly instead of using Selenium.

## Picking the right files
- Each month has a GIS report and a co-located battery report.
  I keep only names starting with "GIS_Report".
- File names are inconsistent ("Jun2026" vs "July2026"), so I don't
  rely on parsing the month from the name.

## Saving files
- Raw files are saved as date_DocID_name.xlsx so a corrected version
  of a month doesn't overwrite the original.
- data/ is in .gitignore because files can be re-downloaded.

## Finding files on disk
- Excel creates hidden lock files (`~$...xlsx`) while a workbook is open.
  The pipeline skips any file starting with `~$`, otherwise it tries to
  read the lock file and crashes.

## Parsing the report
- The project list is on the "Project Details - Large Gen" sheet.
  Small Gen is out of scope for now.
- The header row isn't in a fixed place (row 30 in Large Gen, row 14 in
  Small Gen), so I search for the row whose first cell is "INR" instead of
  hard-coding a row number. If no such row exists, parsing fails with a
  clear error naming the file and sheet.
- I keep 12 of the 31 columns and rename them to snake_case in one
  dictionary (`COLUMNS`). If ERCOT renames a column, it's a one-line fix,
  and the rest of the code is unaffected.
- Rows with no INR are dropped (blank rows above and below the data).
- Project IDs are converted to text and stripped of spaces. Text columns
  are also stripped, because a stray trailing space would otherwise show up
  as a fake "name changed" event when comparing months.
- I don't use `.astype(str)` on text columns that can be empty, because it
  turns missing values into the literal text "nan".

## Things I noticed in the data
- October 2026 has 1,736 Large Gen projects and no duplicate IDs, so
  (file, project_id) can be the primary key.
- The Summary sheet says 1,847 projects. My guess is the difference comes
  from projects that are counted but not listed (the sheet notes mention
  confidentiality), plus Small Gen. So a "row count must match Summary"
  check would be wrong.
- Project IDs don't follow one strict pattern (e.g. `13INR0010a`), so
  validation shouldn't enforce one.
- Capacity can legitimately be negative for modification projects
  (per ERCOT's notes), so validation shouldn't reject negative MW.
- The report has Cancellation Update, Inactive Projects and Commissioning
  Update sheets. When a project disappears between months, I can use these
  to label why: cancelled, inactive, or now operating, and flag anything
  else as unexplained.

## Database
- Using Postgres (in Docker) rather than SQLite, because it's what
  Grid Status uses and it has real DATE and NUMERIC types.
- Planning `NUMERIC` for capacity instead of a float, so decimals are
  stored exactly and don't create fake capacity changes between months.
- Two tables: `files` (one row per report) and `projects` (one row per
  project per report). Keeping a snapshot per month is what makes
  comparing months possible.
- `projects` has a composite primary key (doc_id, project_id): a project
  can appear once per file, never twice in the same file.
- `doc_id` references `files`, so every project row records its source file.
- Each file is loaded in one transaction: the file row and all project rows
  are saved together or not at all. A crash halfway can't leave a file
  marked as loaded with missing projects.
- Re-running is safe: files already in `files` are skipped.
- Values are passed with `%s` placeholders, never pasted into SQL text.
- The connection string comes from the DATABASE_URL environment variable,
  with a local default.

## Comparing months
- New and removed projects are found with LEFT JOIN anti-joins between two
  files' rows in the same `projects` table.
- October check: 1,758 (Sep) − 65 removed + 43 new = 1,736 (Oct). The counts
  reconcile exactly.
- Removed projects are labelled using ERCOT's Cancellation, Inactive and
  Commissioning sheets (stored in `project_events`). In October: 53 cancelled,
  8 commissioned, 2 inactive, 2 unexplained (25INR0220 Hector Solar,
  28INR0043 Sendero Solar). Still investigating those two.
- The Commissioning sheet can list a project more than once (different
  categories), so events are de-duplicated before loading.
- The header search now checks every column for "INR", because in
  Commissioning Update the INR column isn't first.
- Lesson: when loading code changes, already-loaded files are skipped and
  never reprocessed. I had to truncate and reload. A "reload" option would
  fix this properly.
- The Large Gen sheet uses fuel codes (SOL, WIN, ...), while the event sheets
  use full names. The report will need a mapping.

## Change detection
- All change types are saved to one `change_events` table, with old and
  new values stored as text so one table fits dates, statuses and numbers.
  Trade-off: no date math directly on those columns.
- Each comparison deletes its previous results and re-inserts them in one
  transaction, so re-running is safe and picks up query improvements.
- Months are paired automatically (each file with the next by publish date).
- IS DISTINCT FROM is used instead of <> so changes to or from NULL aren't missed.
- A removed project's reasons are combined with STRING_AGG, so a project on
  two event sheets still gets exactly one row.
- Reconciliation: previous total - removed + added = current total, for
  both Aug->Sep and Sep->Oct.
- First finding: in October, 117 projects' dates were pushed later and only
  4 moved earlier.
