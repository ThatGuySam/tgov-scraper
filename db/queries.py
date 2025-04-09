from datetime import datetime, timedelta
from typing import Sequence
from dyntastic import A
from src.models.meeting import Meeting


def get_meetings(days: int = 7) -> Sequence[Meeting]:
    """
    Get meetings that occurred in the past number of days from now.
    """
    now = datetime.now()
    target_date = now - timedelta(days=days)
    meetings = Meeting.scan(
        A.date >= target_date,
    )

    return Sequence(meetings)
