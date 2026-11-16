from datetime import timedelta
from pathlib import Path

from changes import file_pairs
from db import connect

REPORTS_DIR = Path("reports")

LABELS = {
    "added": "New projects",
    "removed": "Removed projects",
    "date_changed": "Projected date changed",
    "status_changed": "Study status changed",
    "capacity_changed": "Capacity changed",
}

FUEL_NAMES = {
    "SOL": "Solar",
    "WIN": "Wind",
    "GAS": "Gas",
    "NUC": "Nuclear",
    "HYD": "Hydro",
    "OIL": "Oil",
    "OTH": "Other",
}

EXTRA_COLUMNS = {
    "added": [],
    "removed": [("Reason", "new")],
    "date_changed": [("Old date", "old"), ("New date", "new")],
    "status_changed": [("Old status", "old"), ("New status", "new")],
    "capacity_changed": [("Old MW", "old"), ("New MW", "new")],
}

DETAIL_SQL = """
    SELECT
        c.project_id,
        COALESCE(cur.project_name, prev.project_name),
        COALESCE(cur.fuel, prev.fuel),
        COALESCE(cur.capacity_mw, prev.capacity_mw),
        c.old_value,
        c.new_value
    FROM change_events AS c
    LEFT JOIN projects AS cur
        ON cur.doc_id = c.cur_doc_id
        AND cur.project_id = c.project_id
    LEFT JOIN projects AS prev
        ON prev.doc_id = c.prev_doc_id
        AND prev.project_id = c.project_id
    WHERE c.prev_doc_id = %(prev)s
      AND c.cur_doc_id = %(cur)s
      AND c.change_type = %(change_type)s
    ORDER BY COALESCE(cur.capacity_mw, prev.capacity_mw) DESC NULLS LAST
"""


def report_month(conn, doc_id):
    publish_date = conn.execute(
        "SELECT publish_date FROM files WHERE doc_id = %s", (doc_id,)
    ).fetchone()[0]
    return (publish_date.replace(day=1) - timedelta(days=1)).replace(day=1)


def summary_lines(conn, prev, cur):
    rows = conn.execute(
        """
        SELECT change_type, COUNT(*)
        FROM change_events
        WHERE prev_doc_id = %s AND cur_doc_id = %s
        GROUP BY change_type
        """,
        (prev, cur),
    ).fetchall()
    counts = dict(rows)

    lines = ["| Change | Projects |", "| --- | --- |"]
    for change_type, label in LABELS.items():
        lines.append(f"| {label} | {counts.get(change_type, 0)} |")
    return lines


def cell(value):
    return "" if value is None else str(value)


def detail_lines(conn, prev, cur, change_type):
    rows = conn.execute(
        DETAIL_SQL, {"prev": prev, "cur": cur, "change_type": change_type}
    ).fetchall()
    if not rows:
        return ["None this month."]

    extras = EXTRA_COLUMNS[change_type]
    headings = ["Project", "Name", "Fuel", "MW"] + [heading for heading, _ in extras]

    lines = [
        "| " + " | ".join(headings) + " |",
        "|" + " --- |" * len(headings),
    ]
    for project_id, name, fuel, mw, old, new in rows:
        stored = {"old": old, "new": new}
        values = [project_id, name, FUEL_NAMES.get(fuel, fuel), mw]
        values += [stored[key] for _, key in extras]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    return lines


def build_report(conn, prev, cur):
    month = report_month(conn, cur)
    previous = report_month(conn, prev)

    lines = [
        f"# ERCOT interconnection queue: what changed in {month:%B %Y}",
        "",
        f"Compared with the {previous:%B %Y} report.",
        "",
        "## Summary",
        "",
    ]
    lines += summary_lines(conn, prev, cur)
    for change_type, label in LABELS.items():
        lines += ["", f"## {label}", ""]
        lines += detail_lines(conn, prev, cur, change_type)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    conn = connect()
    prev, cur = file_pairs(conn)[-1]

    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{report_month(conn, cur):%Y-%m}.md"
    path.write_text(build_report(conn, prev, cur))
    print("Wrote", path)
    conn.close()
