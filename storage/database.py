import sqlite3
import json
from datetime import datetime, timezone
from typing import Iterator
from utils.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL CHECK(source_type IN ('audio', 'text')),
                source_name TEXT NOT NULL,
                checksum TEXT NOT NULL UNIQUE,
                raw_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                processed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS extractions (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                structured_json TEXT,
                model_used TEXT,
                processing_time REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources(id)
            );

            CREATE INDEX IF NOT EXISTS idx_sources_checksum ON sources(checksum);
            CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
            CREATE INDEX IF NOT EXISTS idx_sources_created ON sources(created_at);
            CREATE INDEX IF NOT EXISTS idx_extractions_source ON extractions(source_id);
        """)
        conn.commit()
    finally:
        conn.close()


def source_exists_by_checksum(checksum: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM sources WHERE checksum = ?", (checksum,)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def insert_source(id: str, source_type: str, source_name: str,
                  checksum: str, raw_text: str) -> str:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO sources (id, source_type, source_name, checksum, raw_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (id, source_type, source_name, checksum, raw_text, now)
        )
        conn.commit()
        return id
    except sqlite3.IntegrityError:
        cursor = conn.execute(
            "SELECT id FROM sources WHERE checksum = ?", (checksum,)
        )
        row = cursor.fetchone()
        return row["id"] if row else id
    finally:
        conn.close()


def insert_extraction(id: str, source_id: str, structured: dict,
                      model: str, proc_time: float) -> str:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        structured_json = json.dumps(structured, ensure_ascii=False)
        conn.execute(
            """INSERT INTO extractions (id, source_id, structured_json, model_used, processing_time, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (id, source_id, structured_json, model, proc_time, now)
        )
        conn.execute(
            "UPDATE sources SET processed_at = ? WHERE id = ?",
            (now, source_id)
        )
        conn.commit()
        return id
    finally:
        conn.close()


def get_source_by_checksum(checksum: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM sources WHERE checksum = ?", (checksum,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_extraction_by_source(source_id: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """SELECT e.*, s.source_type, s.source_name, s.checksum,
                      s.raw_text, s.created_at as source_created
               FROM extractions e
               JOIN sources s ON s.id = e.source_id
               WHERE e.source_id = ?
               ORDER BY e.created_at DESC
               LIMIT 1""",
            (source_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def list_sources(limit: int = 50, offset: int = 0) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """SELECT s.*, e.structured_json, e.model_used, e.processing_time
               FROM sources s
               LEFT JOIN extractions e ON e.source_id = s.id
               ORDER BY s.created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def count_sources() -> int:
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM sources")
        row = cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def delete_source(source_id: str) -> bool:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM extractions WHERE source_id = ?", (source_id,))
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()
