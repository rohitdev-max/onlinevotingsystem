from datetime import datetime
from zoneinfo import ZoneInfo


INDIA_TIMEZONE = ZoneInfo('Asia/Kolkata')


def india_now_naive():
    """Return the current India time without timezone metadata for DB comparisons."""
    return datetime.now(INDIA_TIMEZONE).replace(tzinfo=None)