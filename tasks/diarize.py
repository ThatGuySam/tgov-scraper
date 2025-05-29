from src.run_diarization import download_video, run_diarization
from prefect import task

from src.models.meeting import Meeting


@task
def diarize_meeting(meeting: Meeting):
    video_file = download_video(f"{meeting.meeting}_{meeting.date}", str(meeting.video))
    if video_file:
        run_diarization(video_file)
    else:
        print("Video file not found")
    # TODO: Update meeting with transcript location
