from prefect import task
from src.subtitles import create_subtitles
from src.models.subtitles import SubtitleTrack, TrackFormat, Transcript
from pydantic import HttpUrl
from src.http_utils import async_get_json
from src.models.subtitles import TrackFormat


@task
async def create_vtt_track(
    transcript_url: HttpUrl, include_speaker_prefix: bool = False
) -> str:
    transcript_data = await async_get_json(transcript_url.encoded_string())
    transcript = Transcript.model_validate(transcript_data)
    vtt_track: SubtitleTrack = create_subtitles(
        transcript,
        format=TrackFormat.VTT,
        include_speaker_prefix=include_speaker_prefix,
    )
    vtt_content = vtt_track.content()
    # vtt_data = f"data:text/vtt;charset=utf-8;base64,{base64.b64encode(vtt_content.encode('utf-8')).decode('ascii')}"
    return vtt_content
