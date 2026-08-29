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


def get_recent(limit=50, use_case=None, action=None, search=None):
    c = _conn()
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if use_case:
        query += " AND use_case = ?"
        params.append(use_case)
    if action:
        query += " AND action = ?"
        params.append(action)
    if search:
        query += " AND (input_text LIKE ? OR output_text LIKE ? OR reasons LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = c.execute(query, params).fetchall()
    c.close()
    return [dict(r) for r in rows]


def export_audit_log(format: str = "json"):
    c = _conn()
    rows = c.execute("SELECT * FROM audit_log ORDER BY timestamp ASC").fetchall()
    c.close()
    data = [dict(r) for r in rows]
    if format.lower() == "csv":
        import io
        import csv
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()
    return json.dumps(data, indent=2)


def get_action_counts():
    c = _conn()
    rows = c.execute(
        "SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action"
    ).fetchall()
    c.close()
    return {r["action"]: r["cnt"] for r in rows}


def get_feedback_counts():
    c = _conn()
    rows = c.execute(
        """SELECT human_override, COUNT(*) as cnt 
           FROM audit_log 
           WHERE human_override IS NOT NULL AND human_override != '' 
           GROUP BY human_override"""
    ).fetchall()
    c.close()
    counts = {r["human_override"]: r["cnt"] for r in rows}
    total_reviewed = sum(counts.values())
    return {
        "total_reviewed": total_reviewed,
        "correct": counts.get("correct", 0),
        "false_positive": counts.get("false_positive", 0),
        "false_negative": counts.get("false_negative", 0),
    }


def get_system_metrics():
    """
    Computes holistic trustworthiness, precision/recall, and drift analytics.
    """
    c = _conn()
    total_records = c.execute("SELECT COUNT(*) as total FROM audit_log").fetchone()["total"]
    avg_score = c.execute("SELECT AVG(final_score) as avg_score FROM audit_log").fetchone()["avg_score"] or 0.0
    
    actions = get_action_counts()
    fb = get_feedback_counts()
    
    c.close()

    total_reviewed = fb["total_reviewed"]
    correct = fb["correct"]
    fp = fb["false_positive"]
    fn = fb["false_negative"]

    precision = round(correct / (correct + fp), 3) if (correct + fp) > 0 else 1.0
    recall = round(correct / (correct + fn), 3) if (correct + fn) > 0 else 1.0
    f1 = round(2 * (precision * recall) / (precision + recall), 3) if (precision + recall) > 0 else 1.0
    accuracy = round(correct / total_reviewed, 3) if total_reviewed > 0 else 1.0
    fp_rate = round(fp / total_reviewed, 3) if total_reviewed > 0 else 0.0
    fn_rate = round(fn / total_reviewed, 3) if total_reviewed > 0 else 0.0

    # Calibration recommendations
    recommendations = []
    if total_reviewed >= 3:
        if fp_rate > 0.15:
            recommendations.append("High False Positive Rate detected: Consider raising allow_below threshold (+0.05) to reduce alert fatigue.")
        if fn_rate > 0.05:
            recommendations.append("False Negative (missed violation) detected: Consider tightening block_below threshold (-0.05) and checking pii_action floor.")
        if not recommendations:
            recommendations.append("System operating within optimal precision/recall guardrails.")
    else:
        recommendations.append("Collecting human reviewer feedback baseline (minimum 3 sample audits needed).")

    return {
        "total_requests": total_records,
        "average_risk_score": round(avg_score, 3),
        "action_distribution": actions,
        "feedback_summary": fb,
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "false_positive_rate": fp_rate,
            "false_negative_rate": fn_rate,
        },
        "calibration_recommendations": recommendations,
    }


def get_by_id(log_id):
    c = _conn()
    row = c.execute("SELECT * FROM audit_log WHERE id = ?", (log_id,)).fetchone()
    c.close()
    return dict(row) if row else None
