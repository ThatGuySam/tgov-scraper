import asyncio
from prefect import flow
from dyntastic import A
from pydantic import HttpUrl

from src.models.subtitles import Transcript

from tasks.subtitles import create_vtt_track
from db.queries import get_meetings
from src.aws import save_content_to_s3
from src.http_utils import async_get_json


@flow(log_prints=True)
def add_subtitles():
    print("Getting meetings")
    meetings = get_meetings(days=90)
    meetings_with_transcripts = [
        meeting
        for meeting in meetings
        if hasattr(meeting, "transcripts") and meeting.transcripts is not None or []
    ]
    print(f"Found {len(meetings_with_transcripts)} meetings with transcripts")
    for meeting in meetings_with_transcripts:
        for transcript_url in meeting.transcripts:
            print(f"Processing {transcript_url}")
            transcript_data = asyncio.run(
                async_get_json(transcript_url.encoded_string())
            )
            print(f"Transcript data: {transcript_data}")
            transcript = Transcript.model_validate(transcript_data)
            language = transcript.language
            if f"{language}.vtt" in meeting.subtitles:
                continue
            print(f"Creating VTT track for {language}")
            track_content = asyncio.run(
                create_vtt_track(
                    transcript,
                    include_speaker_prefix=False,
                )
            )
            print(f"Saving VTT track to S3")
            result: HttpUrl = save_content_to_s3(
                track_content,
                "tgov-assets",
                f"{meeting.filename()}/subtitles/{language}.vtt",
                "text/vtt",
            )
            print(f"VTT track saved to S3")
            if not meeting.subtitles:
                meeting.subtitles = [result]
            else:
                (
                    meeting.subtitles.append(result)
                    if result not in meeting.subtitles
                    else None
                )
            print(f"Saving meeting to DynamoDB")
            meeting.save()
            print(f"Meeting saved to DynamoDB")


if __name__ == "__main__":
    print("Starting add_subtitles")
    add_subtitles()
