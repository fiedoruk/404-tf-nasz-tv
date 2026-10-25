"""Pure timestamp policy for the Orange PVR metadata refresher."""
import math

CHECK = 1800
FRESH = 6 * 3600
SKEW = 300


def stale(now, mtime):
    return mtime is None or mtime <= 0 or mtime > now + SKEW or now - mtime >= FRESH


def plan(now, state):
    if state and state.get("schema") != 1:
        raise ValueError("Unsupported state schema")
    last = state.get("last_attempt_utc")
    anchor = state.get("cooldown_anchor_utc", last)
    for value in (last, anchor):
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
            raise ValueError("Invalid saved timestamp")
    if anchor is not None and anchor > now + SKEW:
        anchor = now  # Clock rollback: persist one fresh cooldown, retain real attempt.
    updated = {"schema": 1, "last_attempt_utc": last, "cooldown_anchor_utc": anchor}
    return anchor is None or now - anchor >= CHECK, updated


def attempted(now):
    return {"schema": 1, "last_attempt_utc": now, "cooldown_anchor_utc": now}
