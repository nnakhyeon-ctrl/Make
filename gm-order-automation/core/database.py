import sqlite3
from datetime import datetime
from pathlib import Path

from config.settings import DB_PATH
from core.models import Document

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    total_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    source_files TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no TEXT UNIQUE,
    partner TEXT,
    item TEXT,
    item_name TEXT,
    qty TEXT,
    order_date TEXT,
    due_date TEXT,
    status TEXT,
    source_file TEXT,
    run_id INTEGER,
    updated_at TEXT,
    FOREIGN KEY (run_id) REFERENCES runs (id)
);
"""


def get_connection() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def start_run(source_files: list[str]) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO runs (started_at, source_files) VALUES (?, ?)",
        (datetime.now().isoformat(timespec="seconds"), ", ".join(source_files)),
    )
    conn.commit()
    run_id = cur.lastrowid
    conn.close()
    return run_id


def finish_run(run_id: int, total_count: int, fail_count: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE runs SET finished_at = ?, total_count = ?, fail_count = ? WHERE id = ?",
        (datetime.now().isoformat(timespec="seconds"), total_count, fail_count, run_id),
    )
    conn.commit()
    conn.close()


def upsert_documents(documents: list[Document], run_id: int) -> int:
    """Insert new documents or update existing ones matched by doc_no ('DB 반영')."""
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    count = 0
    for doc in documents:
        key = doc.doc_no or f"{doc.item}:{doc.order_date}:{doc.source_file}"
        conn.execute(
            """
            INSERT INTO documents (doc_no, partner, item, item_name, qty, order_date, due_date, status, source_file, run_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_no) DO UPDATE SET
                partner=excluded.partner,
                item=excluded.item,
                item_name=excluded.item_name,
                qty=excluded.qty,
                order_date=excluded.order_date,
                due_date=excluded.due_date,
                status=excluded.status,
                source_file=excluded.source_file,
                run_id=excluded.run_id,
                updated_at=excluded.updated_at
            """,
            (key, doc.partner, doc.item, doc.item_name, doc.qty, doc.order_date,
             doc.due_date, doc.status, doc.source_file, run_id, now),
        )
        count += 1
    conn.commit()
    conn.close()
    return count
