import sqlite3
import json
import time
from app.config import DB_PATH

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL,
    session_id TEXT,
    use_case TEXT,
    input_text TEXT,
    output_text TEXT,
    hallucination_score REAL,
    privacy_score REAL,
    bias_score REAL,
    anomaly_score REAL,
    final_score REAL,
    action TEXT,
    requires_human INTEGER,
    reasons TEXT,
    human_override TEXT,
    reviewer_note TEXT
)
"""

_initialized = False

def _conn():
    global _initialized
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    if not _initialized:
        c.execute(_CREATE_TABLE)
        c.commit()
        _initialized = True
    return c


def log_decision(session_id, use_case, input_text, output_text,
                 components, action, requires_human, reasons):
    c = _conn()
    cur = c.execute(
        """INSERT INTO audit_log
           (timestamp, session_id, use_case, input_text, output_text,
            hallucination_score, privacy_score, bias_score, anomaly_score,
            final_score, action, requires_human, reasons)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            time.time(),
            session_id,
            use_case,
            input_text,
            output_text,
            components.get("hallucination_severity", 0),
            components.get("privacy_signal", 0),
            components.get("bias_signal", 0),
            components.get("anomaly_score", 0),
            components.get("final_score", 0),
            action,
            int(requires_human),
            json.dumps(reasons),
        ),
    )
    c.commit()
    row_id = cur.lastrowid
    c.close()
    return row_id


def record_feedback(log_id, verdict, note=""):
    c = _conn()
    c.execute(
        "UPDATE audit_log SET human_override = ?, reviewer_note = ? WHERE id = ?",
        (verdict, note, log_id),
    )
    c.commit()
    c.close()


def get_recent(limit=50):
    c = _conn()
    rows = c.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_action_counts():
    c = _conn()
    rows = c.execute(
        "SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action"
    ).fetchall()
    c.close()
    return {r["action"]: r["cnt"] for r in rows}


def get_by_id(log_id):
    c = _conn()
    row = c.execute("SELECT * FROM audit_log WHERE id = ?", (log_id,)).fetchone()
    c.close()
    return dict(row) if row else None
