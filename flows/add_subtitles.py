from prefect import flow

from tasks.subtitles import create_vtt_track
from db.queries import get_meetings

from src.models.subtitles import SubtitleTrack, TrackFormat
from src.aws import save_content_to_s3


@flow(log_prints=True)
async def add_subtitles():
    meetings = get_meetings(days=90)
    meetings_with_transcript = [
        meeting
        for meeting in meetings
        if hasattr(meeting, "transcript") and meeting.transcript
    ]
    for meeting in meetings_with_transcript:
        if not meeting.subtitles:
            track_content = await create_vtt_track(
                meeting.transcript,
                include_speaker_prefix=False,
            )
            save_content_to_s3(
                track_content,
                "tgov-assets",
                f"{meeting.filename()}.subtitles.vtt",
                "text/vtt",
            )
    return track_content


if __name__ == "__main__":
    import asyncio

    asyncio.run(add_subtitles())
