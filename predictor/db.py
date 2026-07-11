"""
SQLite persistence for predictions.
Uses the built-in sqlite3 module — zero extra dependencies.
"""

import json
import sqlite3
import time
from typing import Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id                  TEXT NOT NULL,
    timestamp                 TEXT NOT NULL,
    view1_text                TEXT,          -- Signal Analyst
    view2_text                TEXT,          -- Domain Expert
    view3_text                TEXT,          -- Risk Assessor
    view4_text                TEXT,          -- Skeptic
    judge_output_json         TEXT,          -- JSON blob from the Judge
    actual_outcome            INTEGER,       -- NULL until scored later
    actual_outcome_timestamp  TEXT,          -- NULL until scored later
    created_at                TEXT NOT NULL
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure the predictions table exists."""
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    print(f"[DB] Initialised database at {db_path}")
    return conn


def save_prediction(
    conn: sqlite3.Connection,
    asset_id: str,
    timestamp: str,
    view1_text: Optional[str],
    view2_text: Optional[str],
    view3_text: Optional[str],
    view4_text: Optional[str],
    judge_output: dict,
) -> int:
    """
    Insert one prediction row into the table.
    Returns the row ID of the newly inserted record.
    """
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    judge_json = json.dumps(judge_output, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO predictions
            (asset_id, timestamp, view1_text, view2_text, view3_text, view4_text,
             judge_output_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            asset_id,
            timestamp,
            view1_text,
            view2_text,
            view3_text,
            view4_text,
            judge_json,
            created_at,
        ),
    )
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return row_id


def close_db(conn: sqlite3.Connection) -> None:
    """Safely close the database connection."""
    conn.close()