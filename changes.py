from itertools import pairwise

from db import connect


CHANGE_QUERIES = {
    "added": """
        INSERT INTO change_events (prev_doc_id, cur_doc_id, project_id, change_type)
        SELECT %(prev)s, %(cur)s, cur.project_id, 'added'
        FROM projects AS cur
        LEFT JOIN projects AS prev
            ON prev.project_id = cur.project_id
            AND prev.doc_id = %(prev)s
        WHERE cur.doc_id = %(cur)s
          AND prev.project_id IS NULL
    """,
    "removed": """
        INSERT INTO change_events (prev_doc_id, cur_doc_id, project_id, change_type, new_value)
        SELECT
            %(prev)s,
            %(cur)s,
            prev.project_id,
            'removed',
            COALESCE(STRING_AGG(e.event, ', '), 'unexplained')
        FROM projects AS prev
        LEFT JOIN projects AS cur
            ON cur.project_id = prev.project_id
            AND cur.doc_id = %(cur)s
        LEFT JOIN project_events AS e
            ON e.project_id = prev.project_id
            AND e.doc_id = %(cur)s
        WHERE prev.doc_id = %(prev)s
          AND cur.project_id IS NULL
        GROUP BY prev.project_id
    """,
    "date_changed": """
        INSERT INTO change_events
            (prev_doc_id, cur_doc_id, project_id, change_type, old_value, new_value)
        SELECT
            %(prev)s, %(cur)s, cur.project_id, 'date_changed',
            prev.projected_cod::text, cur.projected_cod::text
        FROM projects AS prev
        JOIN projects AS cur
            ON cur.project_id = prev.project_id
            AND cur.doc_id = %(cur)s
        WHERE prev.doc_id = %(prev)s
          AND cur.projected_cod IS DISTINCT FROM prev.projected_cod
    """,
    "status_changed": """
        INSERT INTO change_events
            (prev_doc_id, cur_doc_id, project_id, change_type, old_value, new_value)
        SELECT
            %(prev)s, %(cur)s, cur.project_id, 'status_changed',
            prev.study_phase, cur.study_phase
        FROM projects AS prev
        JOIN projects AS cur
            ON cur.project_id = prev.project_id
            AND cur.doc_id = %(cur)s
        WHERE prev.doc_id = %(prev)s
          AND cur.study_phase IS DISTINCT FROM prev.study_phase
    """,
    "capacity_changed": """
        INSERT INTO change_events
            (prev_doc_id, cur_doc_id, project_id, change_type, old_value, new_value)
        SELECT
            %(prev)s, %(cur)s, cur.project_id, 'capacity_changed',
            prev.capacity_mw::text, cur.capacity_mw::text
        FROM projects AS prev
        JOIN projects AS cur
            ON cur.project_id = prev.project_id
            AND cur.doc_id = %(cur)s
        WHERE prev.doc_id = %(prev)s
          AND cur.capacity_mw IS DISTINCT FROM prev.capacity_mw
    """,
}


CORRECTION_WINDOW_DAYS = 15


def file_pairs(conn):
    rows = conn.execute(
        "SELECT doc_id, publish_date FROM files ORDER BY publish_date, doc_id"
    ).fetchall()

    kept = []
    for doc_id, publish_date in rows:
        if kept and (publish_date - kept[-1][1]).days < CORRECTION_WINDOW_DAYS:
            kept[-1] = (doc_id, publish_date)
        else:
            kept.append((doc_id, publish_date))

    doc_ids = [doc_id for doc_id, _ in kept]
    return list(pairwise(doc_ids))


def detect_changes(conn, prev, cur):
    params = {"prev": prev, "cur": cur}
    with conn.transaction():
        conn.execute(
            "DELETE FROM change_events WHERE prev_doc_id = %(prev)s AND cur_doc_id = %(cur)s",
            params,
        )
        for sql in CHANGE_QUERIES.values():
            conn.execute(sql, params)


if __name__ == "__main__":
    conn = connect()
    conn.execute("DELETE FROM change_events")
    for prev, cur in file_pairs(conn):
        detect_changes(conn, prev, cur)
        print("Compared", prev, "->", cur)

    summary = conn.execute(
        """
        SELECT cur_doc_id, change_type, COUNT(*)
        FROM change_events
        GROUP BY cur_doc_id, change_type
        ORDER BY cur_doc_id, change_type
        """
    ).fetchall()
    for row in summary:
        print(row)
    conn.close()
