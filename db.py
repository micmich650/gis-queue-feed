import os
from pathlib import Path

import psycopg

from parse import parse, parse_events, validate

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://queue:queue@localhost:5432/queue"
)

FIRST_SUPPORTED = "2022-03-01"

DATE_COLUMNS = [
    "projected_cod",
    "ia_signed",
    "approved_energization",
    "approved_synchronization",
]

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS files (
        doc_id       TEXT PRIMARY KEY,
        file_name    TEXT NOT NULL,
        publish_date DATE NOT NULL,
        loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        doc_id                   TEXT NOT NULL REFERENCES files (doc_id),
        project_id               TEXT NOT NULL,
        project_name             TEXT,
        study_phase              TEXT,
        county                   TEXT,
        zone                     TEXT,
        fuel                     TEXT,
        technology               TEXT,
        capacity_mw              NUMERIC,
        projected_cod            DATE,
        ia_signed                DATE,
        approved_energization    DATE,
        approved_synchronization DATE,
        PRIMARY KEY (doc_id, project_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_events (
        doc_id     TEXT NOT NULL REFERENCES files (doc_id),
        project_id TEXT NOT NULL,
        event      TEXT NOT NULL,
        PRIMARY KEY (doc_id, project_id, event)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS change_events (
        prev_doc_id TEXT NOT NULL REFERENCES files (doc_id),
        cur_doc_id  TEXT NOT NULL REFERENCES files (doc_id),
        project_id  TEXT NOT NULL,
        change_type TEXT NOT NULL,
        old_value   TEXT,
        new_value   TEXT,
        PRIMARY KEY (prev_doc_id, cur_doc_id, project_id, change_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quarantine (
        doc_id         TEXT PRIMARY KEY,
        file_name      TEXT NOT NULL,
        reason         TEXT NOT NULL,
        quarantined_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """
]


def connect():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    with conn.transaction():
        for statement in SCHEMA:
            conn.execute(statement)
    return conn

def already_loaded(conn, doc_id):
    row = conn.execute(
        "SELECT 1 FROM files WHERE doc_id = %s", (doc_id,)
    ).fetchone()
    return row is not None


def load_file(conn, path):
    publish_date, doc_id, _ = path.stem.split("_", 2)

    if already_loaded(conn, doc_id):
        print("Already loaded, skipping:", path.name)
        return 0

    df = parse(path)

    problems = validate(df)
    if problems:
        raise ValueError("; ".join(problems))
    
    for col in DATE_COLUMNS:
        df[col] = df[col].dt.date
    df = df.astype(object).where(df.notna(), None)
    df.insert(0, "doc_id", doc_id)

    columns = list(df.columns)
    placeholders = ", ".join("%s" for _ in columns)
    insert_sql = f"INSERT INTO projects ({', '.join(columns)}) VALUES ({placeholders})"

    with conn.transaction():
        conn.execute(
            "INSERT INTO files (doc_id, file_name, publish_date) VALUES (%s, %s, %s)",
            (doc_id, path.name, publish_date),
        )
        with conn.cursor() as cur:
            cur.executemany(insert_sql, df.itertuples(index=False, name=None))
            events = parse_events(path)
            events.insert(0, "doc_id", doc_id)
            conn.execute("DELETE FROM quarantine WHERE doc_id = %s", (doc_id,))
            cur.executemany(
                "INSERT INTO project_events (doc_id, project_id, event) VALUES (%s, %s, %s)",
                events.itertuples(index=False, name=None),
            )

    return len(df)

def quarantine(conn, path, reason):
    _, doc_id, _ = path.stem.split("_", 2)
    conn.execute(
        """
        INSERT INTO quarantine (doc_id, file_name, reason)
        VALUES (%s, %s, %s)
        ON CONFLICT (doc_id)
        DO UPDATE SET reason = EXCLUDED.reason, quarantined_at = now()
        """,
        (doc_id, path.name, reason),
    )


if __name__ == "__main__":
    files = sorted(
        p for p in Path("data/raw").glob("*.xls*") if not p.name.startswith("~$")
    )
    conn = connect()
    for path in files:
        if path.name[:10] < FIRST_SUPPORTED:
            print("Out of scope (old format), skipping:", path.name)
            continue
        try:
            count = load_file(conn, path)
            if count:
                print(f"{path.name}: {count} rows loaded")
        except Exception as error:
            quarantine(conn, path, str(error))
            print(f"QUARANTINED {path.name}: {error}")

    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    print("Total rows in projects table:", total)
    conn.close()