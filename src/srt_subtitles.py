#!/usr/bin/env python
"""
Functions for generating and applying subtitles to videos from transcripts.
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


def get_speaker_color(
    speaker_id: str, color_map: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate a consistent color for a speaker based on their ID.

    Args:
        speaker_id: Unique identifier for the speaker
        color_map: Optional custom mapping of speaker IDs to colors

    Returns:
        Color name
    """
    # Return color from map if provided and speaker exists in it
    if color_map and speaker_id in color_map:
        return color_map[speaker_id]

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


def load_transcript(transcript_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a transcript file and return its data.

    Args:
        transcript_path: Path to the transcript JSON file

    Returns:
        Transcript data as a dictionary
    """
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    return transcript_data


def get_transcript_stats(transcript_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract statistics from a transcript.

    Args:
        transcript_data: Transcript data dictionary

    Returns:
        Dictionary with transcript statistics
    """
    segments = transcript_data.get("segments", [])
    language = transcript_data.get("language", "unknown")

    # Count speakers and words
    speaker_counts = {}
    word_counts = {}
    total_words = 0

    for segment in segments:
        speaker = segment.get("speaker", "Unknown")
        words = segment.get("words", [])
        word_count = len(words)
        total_words += word_count

        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        word_counts[speaker] = word_counts.get(speaker, 0) + word_count

    return {
        "language": language,
        "segment_count": len(segments),
        "total_words": total_words,
        "speaker_counts": speaker_counts,
        "word_counts": word_counts,
    }


def generate_srt_from_json_by_words(
    transcript_data: Union[Dict[str, Any], str, Path],
    output_srt_path: Union[str, Path],
    max_words_per_subtitle: int = 30,
    speaker_prefix: bool = True,
    speaker_color_map: Optional[Dict[str, str]] = None,
    return_subtitles: bool = False,
) -> Dict[str, Any]:
    """
    Convert JSON transcript to SRT subtitle format based on word-level timing.
    Creates new segments when speakers change and limits words per subtitle.

    Args:
        transcript_data: Either a transcript data dictionary or path to JSON file
        output_srt_path: Path where SRT file will be saved
        max_words_per_subtitle: Maximum words per subtitle segment
        speaker_prefix: Whether to include speaker identifiers in subtitles
        speaker_color_map: Optional custom mapping of speaker IDs to colors
        return_subtitles: Whether to return subtitle content in result

    Returns:
        Dictionary with speaker colors and optionally subtitle content
    """
    # Load transcript if a path was provided
    if isinstance(transcript_data, (str, Path)):
        transcript_data = load_transcript(transcript_data)

    segments = transcript_data.get("segments", [])

    # Initialize for processing
    srt_content = []
    subtitle_index = 1
    speaker_colors = {}
    current_words = []
    current_speaker = None
    current_start_time = None
    subtitles_data = []

    # Process each segment to extract word-level information
    for segment in segments:
        speaker = segment.get("speaker", "Unknown")
        words_data = segment.get("words", [])

        if not words_data:
            continue

        # Assign color to speaker if not already assigned
        if speaker not in speaker_colors:
            speaker_colors[speaker] = get_speaker_color(speaker, speaker_color_map)

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

                    # Create text with speaker prefix if enabled
                    speaker_prefix_text = (
                        f"[{current_speaker}] "
                        if speaker_prefix and current_speaker
                        else ""
                    )
                    subtitle_text = speaker_prefix_text + " ".join(
                        [w[0] for w in current_words]
                    )

                    # Create SRT entry
                    srt_entry = (
                        f"{subtitle_index}\n"
                        f"{format_time_for_srt(current_start_time)} --> {format_time_for_srt(last_word_end_time)}\n"
                        f"{subtitle_text}\n\n"
                    )
                    srt_content.append(srt_entry)

                    # Store subtitle data if requested
                    if return_subtitles:
                        subtitles_data.append(
                            {
                                "index": subtitle_index,
                                "start_time": current_start_time,
                                "end_time": last_word_end_time,
                                "duration": last_word_end_time - current_start_time,
                                "speaker": current_speaker,
                                "text": subtitle_text,
                                "word_count": len(current_words),
                            }
                        )

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
        speaker_prefix_text = (
            f"[{current_speaker}] " if speaker_prefix and current_speaker else ""
        )
        subtitle_text = speaker_prefix_text + " ".join([w[0] for w in current_words])

        srt_entry = (
            f"{subtitle_index}\n"
            f"{format_time_for_srt(current_start_time)} --> {format_time_for_srt(last_word_end_time)}\n"
            f"{subtitle_text}\n\n"
        )
        srt_content.append(srt_entry)

        # Store subtitle data if requested
        if return_subtitles:
            subtitles_data.append(
                {
                    "index": subtitle_index,
                    "start_time": current_start_time,
                    "end_time": last_word_end_time,
                    "duration": last_word_end_time - current_start_time,
                    "speaker": current_speaker,
                    "text": subtitle_text,
                    "word_count": len(current_words),
                }
            )

    # Write SRT file
    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.writelines(srt_content)

    result = {"speaker_colors": speaker_colors, "subtitle_count": subtitle_index}

    if return_subtitles:
        result["subtitles"] = subtitles_data

    return result


def convert_srt_to_ass(srt_path: Union[str, Path], ass_path: Union[str, Path]) -> bool:
    """
    Convert SRT subtitle file to ASS format.

    Args:
        srt_path: Path to input SRT file
        ass_path: Path to output ASS file

    Returns:
        True if conversion was successful
    """
    convert_cmd = ["ffmpeg", "-i", str(srt_path), str(ass_path), "-y"]

    try:
        result = subprocess.run(convert_cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting SRT to ASS: {e}")
        print(f"STDERR: {e.stderr}")
        return False


def customize_ass_file(
    ass_path: Union[str, Path],
    speaker_colors: Dict[str, str],
    font_size: int = 24,
    bg_opacity: float = 0.2,
    margin_v: str = "20",
    font_name: str = "Arial",
) -> None:
    """
    Customize an ASS subtitle file to add colors based on speakers.

    Args:
        ass_path: Path to the ASS file
        speaker_colors: Dictionary mapping speaker IDs to colors
        font_size: Font size for subtitles
        bg_opacity: Background opacity (0.0-1.0)
        margin_v: Vertical margin from bottom
        font_name: Font name to use
    """
    # Convert opacity to hex format
    bg_opacity_hex = format(int(bg_opacity * 255), "02x")

    with open(ass_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    for line in lines:
        # Skip any existing color styling
        if line.startswith("Style:"):
            # Replace with our own styling
            output_lines.append(
                f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H{bg_opacity_hex}000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,{margin_v},1\n"
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


def create_subtitled_video(
    video_path: Union[str, Path],
    subtitle_path: Union[str, Path],
    output_path: Union[str, Path],
    font_size: int = 24,
    bg_opacity: float = 0.2,
    subtitle_position: str = "20",
    use_ass: bool = True,
    speaker_colors: Optional[Dict[str, str]] = None,
    font_name: str = "Arial",
) -> bool:
    """
    Add subtitles to a video using ffmpeg.

    Args:
        video_path: Path to input video
        subtitle_path: Path to subtitle file (SRT or ASS)
        output_path: Path for output video
        font_size: Font size for subtitles
        bg_opacity: Background opacity (0.0-1.0)
        subtitle_position: Vertical position from bottom
        use_ass: Whether to convert to ASS for better styling
        speaker_colors: Dictionary mapping speaker IDs to colors (needed for ASS)
        font_name: Font name to use

    Returns:
        True if process was successful
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    subtitle_path = Path(subtitle_path)
    is_ass = subtitle_path.suffix.lower() == ".ass"

    # If we need ASS but have SRT, convert
    if use_ass and not is_ass and speaker_colors:
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tmp:
            ass_path = tmp.name

        try:
            # Convert SRT to ASS
            if not convert_srt_to_ass(subtitle_path, ass_path):
                print("Failed to convert SRT to ASS, falling back to SRT")
                ass_path = subtitle_path
                use_ass = False
            else:
                # Customize ASS with colors
                customize_ass_file(
                    ass_path,
                    speaker_colors,
                    font_size,
                    bg_opacity,
                    subtitle_position,
                    font_name,
                )
        except Exception as e:
            print(f"Error preparing ASS subtitles: {e}")
            ass_path = subtitle_path
            use_ass = False
    else:
        ass_path = subtitle_path

    try:
        # Setup ffmpeg command based on subtitle type
        if use_ass and ass_path.suffix.lower() == ".ass":
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
            # Use SRT with direct styling
            style = f"FontSize={font_size},FontName={font_name},FontColor=white,BackColor=black@{bg_opacity},BorderStyle=3,Alignment=2,MarginV={subtitle_position}"

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vf",
                f"subtitles={subtitle_path}:force_style='{style}'",
                "-c:a",
                "copy",
                str(output_path),
                "-y",
            ]

        # Run ffmpeg command
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Clean up temporary ASS file if created
        if use_ass and ass_path != subtitle_path and os.path.exists(ass_path):
            os.unlink(ass_path)

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error creating subtitled video: {e}")
        print(f"STDERR: {e.stderr}")

        # Clean up temporary ASS file if created
        if use_ass and ass_path != subtitle_path and os.path.exists(ass_path):
            os.unlink(ass_path)

        return False


def extract_clip(
    video_path: Union[str, Path],
    output_path: Union[str, Path],
    start_time: float,
    duration: float,
) -> bool:
    """
    Extract a clip from a video file.

    Args:
        video_path: Path to input video
        output_path: Path for output clip
        start_time: Start time in seconds
        duration: Duration in seconds

    Returns:
        True if process was successful
    """
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-ss",
        str(start_time),
        "-i",
        str(video_path),
        "-t",
        str(duration),
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        str(output_path),
        "-y",
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting clip: {e}")
        print(f"STDERR: {e.stderr}")
        return False


def process_transcript_to_subtitles(
    video_path: Union[str, Path],
    transcript_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    temp_dir: Optional[Union[str, Path]] = None,
    max_words_per_subtitle: int = 30,
    font_size: int = 24,
    bg_opacity: float = 0.2,
    subtitle_position: str = "20",
    speaker_prefix: bool = True,
    speaker_color_map: Optional[Dict[str, str]] = None,
    font_name: str = "Arial",
    keep_temp_files: bool = False,
) -> Dict[str, Any]:
    """
    Process a video with transcript to create a subtitled version.
    Combines multiple steps into a single function.

    Args:
        video_path: Path to the input video file
        transcript_path: Path to the transcript JSON file
        output_path: Path for the output video (if None, will be auto-generated)
        temp_dir: Directory for temporary files (if None, will use system temp)
        max_words_per_subtitle: Maximum words per subtitle
        font_size: Font size for subtitles
        bg_opacity: Background opacity (0.0-1.0)
        subtitle_position: Vertical position from bottom
        speaker_prefix: Whether to include speaker identifiers in subtitles
        speaker_color_map: Optional custom mapping of speaker IDs to colors
        font_name: Font name to use
        keep_temp_files: Whether to keep temporary subtitle files

    Returns:
        Dictionary with results including paths to generated files
    """
    video_path = Path(video_path)
    transcript_path = Path(transcript_path)

    # Create paths
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir()) / "subtitle_processing"
    else:
        temp_dir = Path(temp_dir)

    temp_dir.mkdir(exist_ok=True, parents=True)

    # Generate output path if not provided
    if output_path is None:
        output_filename = f"{video_path.stem}_subtitled{video_path.suffix}"
        output_path = video_path.parent / output_filename
    else:
        output_path = Path(output_path)

    # Create file paths
    srt_path = temp_dir / f"{video_path.stem}.srt"
    ass_path = temp_dir / f"{video_path.stem}.ass"

    results = {
        "video_path": str(video_path),
        "transcript_path": str(transcript_path),
        "output_path": str(output_path),
        "srt_path": str(srt_path),
        "ass_path": str(ass_path),
        "success": False,
    }

    try:
        # Step 1: Generate SRT from transcript
        subtitle_result = generate_srt_from_json_by_words(
            transcript_path,
            srt_path,
            max_words_per_subtitle=max_words_per_subtitle,
            speaker_prefix=speaker_prefix,
            speaker_color_map=speaker_color_map,
            return_subtitles=True,
        )

        speaker_colors = subtitle_result["speaker_colors"]
        results["subtitle_count"] = subtitle_result["subtitle_count"]
        results["speaker_colors"] = speaker_colors

        if "subtitles" in subtitle_result:
            results["subtitles"] = subtitle_result["subtitles"]

        # Step 2: Convert SRT to ASS
        if convert_srt_to_ass(srt_path, ass_path):
            results["srt_to_ass_success"] = True

            # Step 3: Customize ASS file
            customize_ass_file(
                ass_path,
                speaker_colors,
                font_size,
                bg_opacity,
                subtitle_position,
                font_name,
            )

            # Step 4: Create subtitled video using ASS
            if create_subtitled_video(
                video_path,
                ass_path,
                output_path,
                font_size=font_size,
                bg_opacity=bg_opacity,
                subtitle_position=subtitle_position,
                use_ass=True,
                speaker_colors=speaker_colors,
                font_name=font_name,
            ):
                results["success"] = True
        else:
            # Fallback to SRT if ASS conversion fails
            results["srt_to_ass_success"] = False

            # Create subtitled video using SRT
            if create_subtitled_video(
                video_path,
                srt_path,
                output_path,
                font_size=font_size,
                bg_opacity=bg_opacity,
                subtitle_position=subtitle_position,
                use_ass=False,
                font_name=font_name,
            ):
                results["success"] = True

    except Exception as e:
        results["error"] = str(e)

    # Clean up temporary files if not keeping them
    if not keep_temp_files:
        if os.path.exists(srt_path):
            os.unlink(srt_path)
        if os.path.exists(ass_path):
            os.unlink(ass_path)

    return results
