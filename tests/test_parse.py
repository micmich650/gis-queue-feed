import pandas as pd
import pytest

from parse import find_header_row, parse, parse_events

HEADER = [
    "INR",
    "Project Name",
    "GIM Study Phase",
    "County",
    "CDR Reporting Zone",
    "Fuel",
    "Technology",
    "Capacity (MW)",
    "Projected COD",
    "IA Signed",
    "Approved for Energization",
    "Approved for Synchronization",
]


def project_row(project_id):
    return [
        project_id,
        "Test Solar",
        "SS Completed",
        "Bexar",
        "SOUTH",
        "SOL",
        "PV",
        100.0,
        pd.Timestamp("2027-01-01"),
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-06-01"),
        pd.Timestamp("2026-07-01"),
    ]


def write_workbook(path, sheets):
    with pd.ExcelWriter(path) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(
                writer, sheet_name=name, header=False, index=False
            )


def test_finds_header_below_title_rows(tmp_path):
    path = tmp_path / "report.xlsx"
    write_workbook(
        path,
        {
            "Project Details - Large Gen": [
                ["A title"],
                [None],
                HEADER,
                project_row("26INR0001"),
            ]
        },
    )

    assert find_header_row(path, "Project Details - Large Gen") == 2


def test_finds_header_when_inr_is_not_first_column(tmp_path):
    path = tmp_path / "report.xlsx"
    write_workbook(
        path,
        {
            "Commissioning Update": [
                ["A title"],
                ["Category", "INR", "Project Name"],
                ["X", "26INR0001", "A"],
            ]
        },
    )

    assert find_header_row(path, "Commissioning Update") == 1


def test_missing_column_raises_clear_error(tmp_path):
    path = tmp_path / "report.xlsx"
    header = [col for col in HEADER if col != "Capacity (MW)"]
    row = [
        value
        for col, value in zip(HEADER, project_row("26INR0001"))
        if col != "Capacity (MW)"
    ]
    write_workbook(path, {"Project Details - Large Gen": [header, row]})

    with pytest.raises(ValueError, match="Capacity"):
        parse(path)


def test_old_format_sheet_and_column_names(tmp_path):
    path = tmp_path / "report.xlsx"
    old_header = [
        "GINR Study Phase" if col == "GIM Study Phase" else col for col in HEADER
    ]
    write_workbook(path, {"Project Details": [old_header, project_row("20INR0001")]})

    df = parse(path)

    assert df["study_phase"].iloc[0] == "SS Completed"


def test_no_cancellations_note_means_no_events(tmp_path):
    path = tmp_path / "report.xlsx"
    event_table = [["INR", "Project Name"], ["26INR0001", "A"]]
    write_workbook(
        path,
        {
            "Cancellation Update": [
                ["Projects Cancelled"],
                ["No cancelled projects during the month"],
            ],
            "Inactive Projects": event_table,
            "Commissioning Update": event_table,
        },
    )

    events = parse_events(path)

    assert set(events["event"]) == {"inactive", "commissioned"}


def test_event_sheet_with_no_header_and_no_note_fails(tmp_path):
    path = tmp_path / "report.xlsx"
    event_table = [["INR", "Project Name"], ["26INR0001", "A"]]
    write_workbook(
        path,
        {
            "Cancellation Update": [["Something unexpected"]],
            "Inactive Projects": event_table,
            "Commissioning Update": event_table,
        },
    )

    with pytest.raises(ValueError):
        parse_events(path)
