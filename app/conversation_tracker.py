_sessions = {}

ALPHA = 0.3


def update(session_id, current_score, privacy_hit=False):
    if session_id not in _sessions:
        _sessions[session_id] = {
            "momentum": current_score,
            "turn_count": 1,
            "privacy_turns": 1 if privacy_hit else 0,
            "last_privacy_hit": privacy_hit,
        }
        return current_score

    sess = _sessions[session_id]
    prev = sess["momentum"]
    new_momentum = 0.7 * prev + 0.3 * current_score
    sess["momentum"] = new_momentum
    sess["turn_count"] += 1
    sess["last_privacy_hit"] = privacy_hit
    if privacy_hit:
        sess["privacy_turns"] = sess.get("privacy_turns", 0) + 1
    elif current_score <= 0.1 and sess.get("privacy_turns", 0) > 0:
        sess["privacy_turns"] = max(0, sess["privacy_turns"] - 1)
    return new_momentum


def get_momentum(session_id):
    if session_id in _sessions:
        return _sessions[session_id]["momentum"]
    return 0.0


def get_turn_count(session_id):
    if session_id in _sessions:
        return _sessions[session_id]["turn_count"]
    return 0


def should_escalate(session_id, threshold):
    if get_turn_count(session_id) < 2:
        return False
    sess = _sessions.get(session_id, {})
    if get_momentum(session_id) >= threshold:
        return True
    if sess.get("privacy_turns", 0) >= 2 and sess.get("last_privacy_hit", False):
        return True
    return False


def reset(session_id=None):
    if session_id:
        _sessions.pop(session_id, None)
    else:
        _sessions.clear()
