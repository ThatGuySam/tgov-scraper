import json
import os
from typing import Sequence
from src.models.meeting import Meeting

LOCAL_STORE_PATH = "data/meetings.json"

def read_meetings() -> Sequence[Meeting]:
    if not os.path.exists(LOCAL_STORE_PATH):
        return []

    with open(LOCAL_STORE_PATH, 'r') as f:
        data = json.load(f)
        return [Meeting(**meeting) for meeting in data]

def write_meetings(meetings: Sequence[Meeting]):
    os.makedirs(os.path.dirname(LOCAL_STORE_PATH), exist_ok=True)
    with open(LOCAL_STORE_PATH, 'w') as f:
        json_data = [meeting.model_dump_json() for meeting in meetings]
        json.dump(json_data, f)
