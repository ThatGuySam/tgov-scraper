from prefect import flow

from src.meetings import get_registry_meetings, write_registry_meetings
from tasks.subtitles import create_track

from src.models.subtitles import SubtitleTrack, TrackFormat


@flow(log_prints=True)
async def create_subtitles():
    meetings = get_registry_meetings()
    meeting = meetings[0]
    track: SubtitleTrack = await create_track(
        meeting.transcript_url, format=TrackFormat.VTT, include_speaker_prefix=False
    )
    print(track)
    return track


if __name__ == "__main__":
    import asyncio

    asyncio.run(create_subtitles())
