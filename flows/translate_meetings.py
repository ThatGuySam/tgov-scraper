from prefect import flow

from db.queries import get_meetings
from tasks.diarize import diarize_meeting
from tasks.meetings import register_meetings


@flow(log_prints=True)
def translate_meetings():
    new_meetings = register_meetings()
    print(f"Registered {len(new_meetings)} new meetings")
    meetings_to_diarize = get_meetings(video=True)
    print(f"Found {len(meetings_to_diarize)} meetings to diarize")
    for meeting in meetings_to_diarize:
        diarize_meeting(meeting)
    # new_subtitled_video_pages = await create_subtitled_video_pages(new_transcribed_meetings)
    # new_translated_meetings = await translate_transcriptions(new_transcribed_meetings)


if __name__ == "__main__":
    translate_meetings()
