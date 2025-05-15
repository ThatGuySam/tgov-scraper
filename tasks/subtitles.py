from prefect import task
from src.subtitles import create_subtitles
from src.models.subtitles import SubtitleTrack, TrackFormat, Transcript
from pydantic import HttpUrl

from src.models.subtitles import TrackFormat


@task
async def create_vtt_track(
    transcript: Transcript, include_speaker_prefix: bool = False
) -> str:

    vtt_track: SubtitleTrack = create_subtitles(
        transcript,
        format=TrackFormat.VTT,
        include_speaker_prefix=include_speaker_prefix,
    )
    vtt_content = vtt_track.content()
    # vtt_data = f"data:text/vtt;charset=utf-8;base64,{base64.b64encode(vtt_content.encode('utf-8')).decode('ascii')}"
    return vtt_content
