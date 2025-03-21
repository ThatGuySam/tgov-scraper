#!/usr/bin/env python
"""
Script to add subtitles to a video using a JSON transcript and FFmpeg.
"""

import json
import os
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple


def format_time_for_srt(seconds: float) -> str:
    """
    Format time in seconds to SRT format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        String in SRT time format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60
    milliseconds = int((seconds_part - int(seconds_part)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{int(seconds_part):02d},{milliseconds:03d}"


def get_speaker_color(speaker_id: str) -> str:
    """
    Generate a consistent color for a speaker based on their ID.

    Args:
        speaker_id: Unique identifier for the speaker

    Returns:
        Hex color code
    """
    # Define a list of easy-to-distinguish colors
    colors = [
        "yellow",
        "cyan",
        "lime",
        "magenta",
        "red",
        "aqua",
        "chartreuse",
        "coral",
        "gold",
        "pink",
        "lavender",
        "orange",
        "orchid",
        "plum",
        "salmon",
    ]

    # Use a hash of the speaker ID to consistently assign colors
    hash_val = int(hashlib.md5(speaker_id.encode()).hexdigest(), 16)
    return colors[hash_val % len(colors)]


def split_text_into_chunks(text: str, max_words: int = 30) -> List[str]:
    """
    Split text into smaller chunks by word count.

    Args:
        text: Input text to split
        max_words: Maximum words per chunk

    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)

    return chunks


def generate_srt_from_json_by_words(
    json_path: Union[str, Path],
    output_srt_path: Union[str, Path],
    max_words_per_subtitle: int = 30,
) -> Dict[str, str]:
    """
    Convert JSON transcript to SRT subtitle format based on word-level timing.
    Creates new segments when speakers change and limits words per subtitle.

    Args:
        json_path: Path to JSON transcript file
        output_srt_path: Path where SRT file will be saved
        max_words_per_subtitle: Maximum words per subtitle segment

    Returns:
        Dictionary mapping speaker IDs to their assigned colors
    """
    # Load JSON transcript
    with open(json_path, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    segments = transcript_data.get("segments", [])

    # Initialize for processing
    srt_content = []
    subtitle_index = 1
    speaker_colors = {}
    current_words = []
    current_speaker = None
    current_start_time = None

    # Process each segment to extract word-level information
    for segment in segments:
        speaker = segment.get("speaker", "Unknown")
        words_data = segment.get("words", [])

        if not words_data:
            continue

        # Assign color to speaker if not already assigned
        if speaker not in speaker_colors:
            speaker_colors[speaker] = get_speaker_color(speaker)

        for word_data in words_data:
            word = word_data.get("word", "").strip()
            word_start = word_data.get("start", 0)
            word_end = word_data.get("end", 0)
            word_speaker = word_data.get("speaker", speaker)

            if not word:
                continue

            # If speaker changes or we've reached max words, create a new subtitle
            if (current_speaker and current_speaker != word_speaker) or (
                len(current_words) >= max_words_per_subtitle and current_words
            ):

                # Create subtitle for accumulated words
                if current_words and current_start_time is not None:
                    # Get the end time from the last word in current_words
                    last_word_end_time = current_words[-1][2]  # (word, start, end)

                    # Create text with speaker prefix
                    speaker_prefix = f"[{current_speaker}] " if current_speaker else ""
                    subtitle_text = speaker_prefix + " ".join(
                        [w[0] for w in current_words]
                    )

                    # Create SRT entry
                    srt_entry = (
                        f"{subtitle_index}\n"
                        f"{format_time_for_srt(current_start_time)} --> {format_time_for_srt(last_word_end_time)}\n"
                        f"{subtitle_text}\n\n"
                    )
                    srt_content.append(srt_entry)
                    subtitle_index += 1

                # Reset for next subtitle
                current_words = []
                current_start_time = word_start
                current_speaker = word_speaker

            # If this is the first word in a new subtitle
            if not current_words:
                current_start_time = word_start
                current_speaker = word_speaker

            # Add word to current collection
            current_words.append((word, word_start, word_end))

    # Add the last subtitle if there are remaining words
    if current_words and current_start_time is not None:
        last_word_end_time = current_words[-1][2]
        speaker_prefix = f"[{current_speaker}] " if current_speaker else ""
        subtitle_text = speaker_prefix + " ".join([w[0] for w in current_words])

        srt_entry = (
            f"{subtitle_index}\n"
            f"{format_time_for_srt(current_start_time)} --> {format_time_for_srt(last_word_end_time)}\n"
            f"{subtitle_text}\n\n"
        )
        srt_content.append(srt_entry)

    # Write SRT file
    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.writelines(srt_content)

    print(f"SRT file created at: {output_srt_path} with {subtitle_index} subtitles")
    return speaker_colors


def create_subtitled_video_with_ffmpeg(
    video_path: Union[str, Path],
    srt_path: Union[str, Path],
    output_path: Union[str, Path],
    speaker_colors: Optional[Dict[str, str]] = None,
    font_size: int = 20,
    bg_opacity: float = 0.2,  # More transparent background
    subtitle_position: str = "20",  # Position from bottom
) -> None:
    """
    Add subtitles to video using ffmpeg.

    Args:
        video_path: Path to input video
        srt_path: Path to SRT subtitles
        output_path: Path for output video
        speaker_colors: Dictionary mapping speaker IDs to colors
        font_size: Font size for subtitles
        bg_opacity: Background opacity (0.0-1.0)
        subtitle_position: Vertical position from bottom
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert opacity to hex
    bg_opacity_hex = format(int(bg_opacity * 255), "02x")

    if speaker_colors:
        # For diarized transcripts, we'll use ASS subtitles to support per-speaker colors
        # First, convert SRT to ASS format
        ass_path = str(srt_path) + ".ass"

        convert_cmd = ["ffmpeg", "-i", str(srt_path), str(ass_path), "-y"]

        print(f"Converting SRT to ASS: {' '.join(convert_cmd)}")
        subprocess.run(convert_cmd, check=True, capture_output=True, text=True)

        # Customize the ASS file to add colors
        customize_ass_file(
            ass_path, speaker_colors, font_size, bg_opacity_hex, subtitle_position
        )

        # Use the ASS file for subtitling
        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vf",
            f"ass={ass_path}",
            "-c:a",
            "copy",
            str(output_path),
            "-y",
        ]
    else:
        # For non-diarized transcripts, use simpler approach
        style = f"FontSize={font_size},FontColor=white,BackColor=black@{bg_opacity},BorderStyle=3,Alignment=2,MarginV={subtitle_position}"

        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vf",
            f"subtitles={srt_path}:force_style='{style}'",
            "-c:a",
            "copy",
            str(output_path),
            "-y",
        ]

    # Run ffmpeg command
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Subtitled video created successfully at: {output_path}")
    else:
        print(f"Error creating subtitled video: {result.stderr}")

    # Clean up ASS file if it was created
    if speaker_colors and os.path.exists(ass_path):
        os.unlink(ass_path)


def customize_ass_file(
    ass_path: str,
    speaker_colors: Dict[str, str],
    font_size: int,
    bg_opacity_hex: str,
    margin_v: str,
) -> None:
    """
    Customize an ASS subtitle file to add colors based on speakers.

    Args:
        ass_path: Path to the ASS file
        speaker_colors: Dictionary mapping speaker IDs to colors
        font_size: Font size for subtitles
        bg_opacity_hex: Background opacity in hex format
        margin_v: Vertical margin from bottom
    """
    with open(ass_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    for line in lines:
        # Skip any existing color styling
        if line.startswith("Style:"):
            # Replace with our own styling
            output_lines.append(
                f"Style: Default,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,&H{bg_opacity_hex}000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,{margin_v},1\n"
            )
        elif line.startswith("Dialogue:"):
            # Extract text and check for speaker
            parts = line.split(",", 9)
            if len(parts) >= 10:
                text = parts[9].strip()

                # Check for speaker tag [SPEAKER_XX]
                for speaker, color in speaker_colors.items():
                    speaker_tag = f"[{speaker}]"
                    if speaker_tag in text:
                        # Add color override at the beginning of the line
                        color_code = get_color_code_for_ass(color)
                        styled_text = f"{{\\c&H{color_code}&}}{text}"
                        parts[9] = styled_text
                        line = ",".join(parts)
                        break

            output_lines.append(line)
        else:
            output_lines.append(line)

    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)


def get_color_code_for_ass(color_name: str) -> str:
    """
    Convert color name to ASS color code (BGR format).

    Args:
        color_name: Name of the color

    Returns:
        ASS color code in BGR format
    """
    # Define color mappings in BGR format (reversed from RGB)
    color_map = {
        "white": "FFFFFF",
        "yellow": "00FFFF",
        "cyan": "FFFF00",
        "lime": "00FF00",
        "magenta": "FF00FF",
        "red": "0000FF",
        "aqua": "FFFF00",
        "chartreuse": "00FF7F",
        "coral": "507FFF",
        "gold": "00D7FF",
        "pink": "CBC0FF",
        "lavender": "FAE6E6",
        "orange": "00A5FF",
        "orchid": "D670DA",
        "plum": "DDA0DD",
        "salmon": "7280FA",
    }

    return color_map.get(color_name, "FFFFFF")  # Default to white if color not found


def process_video_with_transcript(
    video_path: Union[str, Path],
    transcript_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    font_size: int = 20,
    bg_opacity: float = 0.2,
    max_words_per_subtitle: int = 30,
) -> None:
    """
    Process a video with transcript to create a subtitled version.

    Args:
        video_path: Path to the input video file
        transcript_path: Path to the transcript JSON file
        output_path: Path for the output video (if None, will be auto-generated)
        font_size: Font size for subtitles
        bg_opacity: Background opacity (0.0-1.0)
        max_words_per_subtitle: Maximum words per subtitle
    """
    video_path = Path(video_path)
    transcript_path = Path(transcript_path)

    # Generate output path if not provided
    if output_path is None:
        output_filename = f"{video_path.stem}_word_based_subtitles{video_path.suffix}"
        output_path = video_path.parent / output_filename

    # Create temporary SRT file
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
        srt_path = tmp.name

    try:
        # Generate SRT from JSON transcript with word-level timing
        speaker_colors = generate_srt_from_json_by_words(
            transcript_path,
            srt_path,
            max_words_per_subtitle=max_words_per_subtitle,
        )

        # Create subtitled video
        create_subtitled_video_with_ffmpeg(
            video_path=video_path,
            srt_path=srt_path,
            output_path=output_path,
            speaker_colors=speaker_colors,
            font_size=font_size,
            bg_opacity=bg_opacity,
        )
    finally:
        # Clean up temporary file
        if os.path.exists(srt_path):
            os.unlink(srt_path)


if __name__ == "__main__":
    # Path to the meeting video
    VIDEO_PATH = Path("data/video/regular_council_meeting___2025_02_26.mp4")

    # Path to the transcript (must have word-level timing)
    TRANSCRIPT_PATH = Path(
        "data/transcripts/regular_council_meeting___2025_02_26.diarized.json"
    )

    # Output path
    OUTPUT_PATH = Path(
        "data/video/regular_council_meeting___2025_02_26_word_subtitled.mp4"
    )

    # Generate subtitled video
    process_video_with_transcript(
        video_path=VIDEO_PATH,
        transcript_path=TRANSCRIPT_PATH,
        output_path=OUTPUT_PATH,
        font_size=24,  # Font size
        bg_opacity=0.2,  # More transparent background
        max_words_per_subtitle=30,  # Limit words per subtitle
    )
