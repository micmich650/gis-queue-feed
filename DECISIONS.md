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