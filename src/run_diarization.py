import asyncio


from pathlib import Path

from src.models.meeting import GranicusPlayerPage
from src.granicus import get_video_player
from src.videos import download_file, transcribe_video_with_diarization


def download_video():
    # Create output directory if it doesn't exist
    VIDEO_DIRECTORY = Path("data/video")
    VIDEO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    file_name = "regular_council_meeting___2025_03_26"

    # Define output path for the video
    output_path = VIDEO_DIRECTORY / f"{file_name}.mp4"

    # video_url = "https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id=6501"
    # video_url = "https://tulsa-ok.granicus.com/player/clip/6578?view_id=4&redirect=true"
    video_url = "https://tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&clip_id=4274"
    print(f"Downloading video from {video_url}")
    # Get video player page info
    player_page: GranicusPlayerPage = asyncio.run(get_video_player(video_url))

    # Run the download
    video_file = download_file(player_page.download_url, output_path)

    # Display the result
    if video_file:
        print(f"Video saved to: {video_file}")

    return video_file


def run_diarization(video_file: Path):
    transcription_dir = Path("data/transcripts")

    transcription = asyncio.run(
        transcribe_video_with_diarization(video_file, transcription_dir)
    )
    print(transcription)


if __name__ == "__main__":
    video_file = download_video()
    if video_file:
        run_diarization(video_file)
    else:
        print("Video file not found")
