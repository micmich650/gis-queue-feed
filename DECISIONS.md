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