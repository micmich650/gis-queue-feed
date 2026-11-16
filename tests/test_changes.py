import psycopg
import pytest

from changes import detect_changes
from db import connect

TEST_URL = "postgresql://queue:queue@localhost:5432/queue_test"


@pytest.fixture
def conn():
    try:
        conn = connect(TEST_URL)
    except psycopg.OperationalError:
        pytest.skip("test database not available")
    conn.execute("TRUNCATE change_events, project_events, projects, quarantine, files")
    yield conn
    conn.close()


def add_file(conn, doc_id, publish_date):
    conn.execute(
        "INSERT INTO files (doc_id, file_name, publish_date) VALUES (%s, %s, %s)",
        (doc_id, f"{doc_id}.xlsx", publish_date),
    )


def add_project(
    conn, doc_id, project_id, status="SS Completed", mw=100, cod="2027-01-01"
):
    conn.execute(
        """
        INSERT INTO projects (doc_id, project_id, study_phase, capacity_mw, projected_cod)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (doc_id, project_id, status, mw, cod),
    )


def test_detects_each_kind_of_change(conn):
    add_file(conn, "sep", "2026-10-01")
    add_file(conn, "oct", "2026-11-02")

    add_project(conn, "sep", "A")
    add_project(conn, "sep", "B")
    add_project(conn, "sep", "C")
    add_project(conn, "sep", "E")

    add_project(conn, "oct", "B", cod="2027-06-01")
    add_project(conn, "oct", "C", status="FIS Completed", mw=120)
    add_project(conn, "oct", "D")

    conn.execute(
        "INSERT INTO project_events (doc_id, project_id, event) VALUES ('oct', 'A', 'cancelled')"
    )

    detect_changes(conn, "sep", "oct")

    rows = conn.execute(
        "SELECT project_id, change_type, old_value, new_value FROM change_events"
    ).fetchall()
    assert set(rows) == {
        ("A", "removed", None, "cancelled"),
        ("E", "removed", None, "unexplained"),
        ("B", "date_changed", "2027-01-01", "2027-06-01"),
        ("C", "status_changed", "SS Completed", "FIS Completed"),
        ("C", "capacity_changed", "100", "120"),
        ("D", "added", None, None),
    }


def test_running_twice_gives_same_result(conn):
    add_file(conn, "sep", "2026-10-01")
    add_file(conn, "oct", "2026-11-02")
    add_project(conn, "sep", "A")
    add_project(conn, "oct", "B")

    detect_changes(conn, "sep", "oct")
    detect_changes(conn, "sep", "oct")

    count = conn.execute("SELECT COUNT(*) FROM change_events").fetchone()[0]
    assert count == 2
