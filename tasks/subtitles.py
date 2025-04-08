from prefect import task
from src.subtitles import create_track, request_transcript
from src.models.subtitles import SubtitleTrack, TrackFormat
from pydantic import BaseModel, HttpUrl
import base64


class CreateTrackParams(BaseModel):
    transcript_url: HttpUrl
    format: TrackFormat
    include_speaker_prefix: bool = False


@task
async def create_track(params: CreateTrackParams) -> str:
    transcript = await request_transcript(params.transcript_url)
    vtt_track: SubtitleTrack = create_track(
        transcript, params.format, params.include_speaker_prefix
    )
    vtt_content = vtt_track.content()
    vtt_data = f"data:text/vtt;charset=utf-8;base64,{base64.b64encode(vtt_content.encode('utf-8')).decode('ascii')}"
    return vtt_data
