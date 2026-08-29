from app import audit_log


def submit_feedback(log_id, verdict, note=""):
    entry = audit_log.get_by_id(log_id)
    if not entry:
        return False
    audit_log.record_feedback(log_id, verdict, note)
    return True
