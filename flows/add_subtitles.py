from prefect import flow
from dyntastic import A
from pydantic import HttpUrl

from src.models.subtitles import Transcript

from tasks.subtitles import create_vtt_track
from db.queries import get_meetings
from src.aws import save_content_to_s3
from src.http_utils import async_get_json


@flow(log_prints=True)
async def add_subtitles():
    meetings = get_meetings(days=90)
    meetings_with_transcripts = [
        meeting
        for meeting in meetings
        if hasattr(meeting, "transcripts") and meeting.transcripts is not None or []
    ]
    for meeting in meetings_with_transcripts:
        for transcript_url in meeting.transcripts:
            transcript_data = await async_get_json(transcript_url.encoded_string())
            transcript = Transcript.model_validate(transcript_data)
            language = transcript.language
            if f"{language}.vtt" in meeting.subtitles:
                continue
            track_content = await create_vtt_track(
                transcript,
                include_speaker_prefix=False,
            )
            result: HttpUrl = save_content_to_s3(
                track_content,
                "tgov-assets",
                f"{meeting.filename()}/subtitles/{language}.vtt",
                "text/vtt",
            )
            if not meeting.subtitles:
                meeting.subtitles = [result]
            else:
                (
                    meeting.subtitles.append(result)
                    if result not in meeting.subtitles
                    else None
                )
            meeting.save()


if __name__ == "__main__":
    import asyncio

    asyncio.run(add_subtitles())
