#!/usr/bin/env python
"""
Unified Subtitles Module

Provides functions for generating subtitle tracks in different formats (SRT, ASS, VTT)
from diarized transcripts. Supports automatic speaker coloring and optimal chunking.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import aiohttp
from pydantic import HttpUrl

# Import models from the models module
from src.models.subtitles import (
    TrackFormat,
    SpeakerInfo,
    SrtEntry,
    VttEntry,
    AssEntry,
    TrackMetadata,
    SubtitleTrack,
    Transcript,
    AssStyle,
)


def format_time_for_srt(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        String in SRT time format
    """

    # Create a datetime object from seconds
    time_obj = datetime(1, 1, 1) + timedelta(seconds=seconds)

    # Format using strftime for hours, minutes, seconds
    time_str = time_obj.strftime("%H:%M:%S")

    # Add milliseconds
    milliseconds = int((seconds % 1) * 1000)

    return f"{time_str},{milliseconds:03d}"


def format_time_for_vtt(seconds: float) -> str:
    """
    Convert seconds to WebVTT timestamp format (HH:MM:SS.mmm)

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds_remainder:06.3f}"


def format_time_for_ass(seconds: float) -> str:
    """
    Convert seconds to ASS timestamp format (H:MM:SS.cc)

    Args:
        seconds: Time in seconds

    Returns:
        String in ASS time format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60
    centiseconds = int((seconds_part - int(seconds_part)) * 100)

    return f"{hours}:{minutes:02d}:{int(seconds_part):02d}.{centiseconds:02d}"


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


def chunk_transcript(
    transcript: Transcript,
    max_duration: float = 5.0,
    max_length: int = 80,
    max_words: int = 14,
    min_duration: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Chunk transcript segments into appropriate subtitle-sized chunks.
    Uses a hybrid approach that considers:
    - Duration limits
    - Character length limits
    - Word count limits
    - Speaker changes
    - Natural punctuation breaks

    Args:
        transcript: Validated transcript object
        max_duration: Maximum duration in seconds for a subtitle
        max_length: Maximum character length for a subtitle line
        max_words: Maximum number of words per subtitle
        min_duration: Minimum duration in seconds for a subtitle

    Returns:
        List of chunked subtitle objects
    """
    chunks = []
    current_chunk = {"text": "", "start": 0, "end": 0, "speaker": "", "words": []}
    for segment in transcript.segments:
        # Skip very short segments
        if segment.end - segment.start < 0.1:
            continue

        # If we don't have word-level information, use the segment text
        if not segment.words:
            # Process segment by checking if it needs splitting
            if (
                segment.end - segment.start > max_duration
                or len(segment.text) > max_length
            ):
                # Split by punctuation
                parts = re.split(r"([.!?,:;])", segment.text)
                text_parts = []

                current_part = ""
                for i in range(0, len(parts), 2):
                    part = parts[i]
                    punctuation = parts[i + 1] if i + 1 < len(parts) else ""

                    if len(current_part + part + punctuation) > max_length:
                        if current_part:
                            text_parts.append(current_part.strip())
                        current_part = part + punctuation
                    else:
                        current_part += part + punctuation

                if current_part:
                    text_parts.append(current_part.strip())

                # If we still have long parts, split by words
                final_parts = []
                for part in text_parts:
                    if len(part) > max_length:
                        words = part.split()
                        current_words = []

                        for word in words:
                            if (
                                len(" ".join(current_words + [word])) > max_length
                                or len(current_words) >= max_words
                            ):
                                final_parts.append(" ".join(current_words))
                                current_words = [word]
                            else:
                                current_words.append(word)

                        if current_words:
                            final_parts.append(" ".join(current_words))
                    else:
                        final_parts.append(part)

                # Calculate timestamps for each part
                total_duration = segment.end - segment.start
                for i, part in enumerate(final_parts):
                    part_ratio = (
                        len(part) / len(segment.text)
                        if segment.text
                        else 1.0 / len(final_parts)
                    )
                    part_duration = total_duration * part_ratio

                    part_start = (
                        segment.start
                        + (
                            total_duration
                            * (sum(len(p) for p in final_parts[:i]) / len(segment.text))
                        )
                        if segment.text
                        else segment.start
                    )
                    part_end = min(part_start + part_duration, segment.end)

                    # Ensure minimum duration
                    if part_end - part_start < min_duration:
                        part_end = part_start + min_duration

                    chunks.append(
                        {
                            "start": part_start,
                            "end": part_end,
                            "text": part.strip(),
                            "speaker": segment.speaker,
                            "words": [],
                        }
                    )
            else:
                # Add segment as is
                chunks.append(
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "speaker": segment.speaker,
                        "words": [],
                    }
                )
        else:
            # Process using word-level information
            current_words = []
            current_speaker = None
            current_start = None

            for word_obj in segment.words:
                word = word_obj.word.strip()
                word_start = word_obj.start
                word_end = word_obj.end
                word_speaker = word_obj.speaker or segment.speaker

                if not word:
                    continue

                # Check if we should start a new subtitle
                new_subtitle_needed = (
                    # Speaker change
                    (current_speaker and current_speaker != word_speaker)
                    or
                    # Too many words
                    (len(current_words) >= max_words)
                    or
                    # Too long duration
                    (current_start and word_end - current_start > max_duration)
                    or
                    # Text would be too long
                    (
                        len(" ".join([w["word"] for w in current_words] + [word]))
                        > max_length
                    )
                )

                if new_subtitle_needed and current_words:
                    # Finalize current subtitle
                    text = " ".join([w["word"] for w in current_words])
                    last_word_end = current_words[-1]["end"]

                    chunks.append(
                        {
                            "start": current_start,
                            "end": last_word_end,
                            "text": text,
                            "speaker": current_speaker,
                            "words": current_words.copy(),
                        }
                    )

                    # Reset for next subtitle
                    current_words = []
                    current_start = word_start
                    current_speaker = word_speaker

                # If this is the first word in a subtitle
                if not current_words:
                    current_start = word_start
                    current_speaker = word_speaker

                # Add word to current subtitle
                current_words.append(
                    {
                        "word": word,
                        "start": word_start,
                        "end": word_end,
                        "speaker": word_speaker,
                    }
                )

            # Add final subtitle from any remaining words
            if current_words and current_start is not None:
                text = " ".join([w["word"] for w in current_words])
                last_word_end = current_words[-1]["end"]

                chunks.append(
                    {
                        "start": current_start,
                        "end": last_word_end,
                        "text": text,
                        "speaker": current_speaker,
                        "words": current_words.copy(),
                    }
                )

    return chunks


def add_speaker_prefixes(
    chunks: List[Dict[str, Any]],
    prefix_format: str = "[{speaker}] ",
    use_numeric_speakers: bool = False,
) -> List[Dict[str, Any]]:
    """
    Add speaker prefixes to subtitle text.

    Args:
        chunks: List of chunked subtitle objects
        prefix_format: Format string for the speaker prefix
        use_numeric_speakers: Use numeric speaker IDs instead of full IDs

    Returns:
        Updated list of chunks with speaker prefixes
    """
    speaker_mapping = {}
    current_speaker_number = 1

    for chunk in chunks:
        speaker = chunk.get("speaker")
        if not speaker:
            continue

        # Create a numeric mapping if requested
        if use_numeric_speakers:
            if speaker not in speaker_mapping:
                speaker_mapping[speaker] = f"Speaker {current_speaker_number}"
                current_speaker_number += 1
            display_speaker = speaker_mapping[speaker]
        else:
            # Clean up the speaker ID (e.g., "SPEAKER_01" -> "Speaker 1")
            if speaker.startswith("SPEAKER_"):
                display_speaker = "Speaker " + speaker.replace("SPEAKER_", "").lstrip(
                    "0"
                )
            else:
                display_speaker = speaker

        # Add the prefix
        chunk["text"] = prefix_format.format(speaker=display_speaker) + chunk["text"]

    return chunks


def create_subtitles(
    transcript: Transcript,
    format: str = "srt",
    max_duration: float = 5.0,
    max_length: int = 80,
    max_words: int = 14,
    min_duration: float = 0.5,
    include_speaker_prefix: bool = True,
    speaker_color_map: Optional[Dict[str, str]] = None,
    font_name: str = "Arial",
    font_size: int = 24,
    bg_opacity: float = 0.5,
    title: Optional[str] = None,
) -> SubtitleTrack:
    """
    Create a subtitle track from a transcript in the specified format.

    Args:
        transcript_data: Either a transcript data dictionary or path to JSON file
        format: Format of the subtitle track ("srt", "ass", or "vtt")
        max_duration: Maximum duration in seconds for a subtitle
        max_length: Maximum character length for a subtitle line
        max_words: Maximum words per subtitle
        min_duration: Minimum duration in seconds for a subtitle
        include_speaker_prefix: Whether to include speaker IDs in the subtitles
        speaker_color_map: Optional custom mapping of speaker IDs to colors
        font_name: Font name for ASS subtitles
        font_size: Font size for ASS subtitles
        bg_opacity: Background opacity (0.0-1.0) for ASS subtitles
        title: Optional title for the subtitle track

    Returns:
        SubtitleTrack object containing metadata and subtitle entries
    """
    # Normalize track format to TrackFormat enum internally
    track_format = TrackFormat(format.lower())
    # Chunk the transcript
    chunks = chunk_transcript(
        transcript,
        max_duration=max_duration,
        max_length=max_length,
        max_words=max_words,
        min_duration=min_duration,
    )

    # Add speaker prefixes if requested
    if include_speaker_prefix:
        chunks = add_speaker_prefixes(chunks)

    # Determine track duration
    track_duration = max(chunk["end"] for chunk in chunks) if chunks else 0

    # Count total words
    word_count = sum(
        (
            len(chunk.get("words", []))
            if chunk.get("words")
            else len(chunk["text"].split())
        )
        for chunk in chunks
    )

    # Generate speaker colors
    speakers = {}
    for chunk in chunks:
        speaker_id = chunk.get("speaker")
        if speaker_id and speaker_id not in speakers:
            color = get_speaker_color(speaker_id, speaker_color_map)
            display_name = None

            # Generate a display name (e.g., "Speaker 1" from "SPEAKER_01")
            if speaker_id.startswith("SPEAKER_"):
                display_name = (
                    f"Speaker {speaker_id.replace('SPEAKER_', '').lstrip('0')}"
                )

            speakers[speaker_id] = SpeakerInfo(
                id=speaker_id, color=color, display_name=display_name
            )

    # Create metadata
    metadata = TrackMetadata(
        format=track_format,
        language=transcript.language,
        title=title,
        speakers=speakers,
        word_count=word_count,
        duration=track_duration,
        style=AssStyle(
            font_name=font_name,
            font_size=font_size,
            back_color="000000",
        ),
    )

    # Create entries based on format
    entries = []

    if track_format == TrackFormat.SRT:
        for i, chunk in enumerate(chunks):
            entry = SrtEntry(
                index=i + 1,
                start=chunk["start"],
                end=chunk["end"],
                text=chunk["text"],
                speaker_id=chunk.get("speaker"),
                word_count=(
                    len(chunk.get("words", []))
                    if chunk.get("words")
                    else len(chunk["text"].split())
                ),
            )
            entries.append(entry)

    elif track_format == TrackFormat.VTT:
        for i, chunk in enumerate(chunks):
            # For VTT, we can add speaker styling with the <v> tag
            text = chunk["text"]
            speaker_id = chunk.get("speaker")

            # Add speaker voice tag if we have a speaker but no prefix (to avoid duplication)
            if speaker_id and not include_speaker_prefix:
                display_name = (
                    speakers[speaker_id].display_name
                    if speaker_id in speakers
                    else speaker_id
                )
                text = f"<v {display_name}>{text}</v>"

            entry = VttEntry(
                index=i + 1,
                start=chunk["start"],
                end=chunk["end"],
                text=text,
                speaker_id=speaker_id,
                word_count=(
                    len(chunk.get("words", []))
                    if chunk.get("words")
                    else len(chunk["text"].split())
                ),
            )
            entries.append(entry)

    elif track_format == TrackFormat.ASS:
        for i, chunk in enumerate(chunks):
            speaker_id = chunk.get("speaker")
            text = chunk["text"]
            styled_text = text

            # Apply color styling for the speaker
            if speaker_id and speaker_id in speakers:
                # Use the speaker's style if available
                style_name = f"Speaker_{speaker_id.replace('SPEAKER_', '')}"
                color_code = get_color_code_for_ass(speakers[speaker_id].color)

                # Only add color code if we're not using a specific style
                styled_text = f"{{\\c&H{color_code}&}}{text}"

            entry = AssEntry(
                index=i + 1,
                start=chunk["start"],
                end=chunk["end"],
                text=text,
                styled_text=styled_text,
                speaker_id=speaker_id,
                style=(
                    "Default"
                    if not speaker_id
                    else f"Speaker_{speaker_id.replace('SPEAKER_', '')}"
                ),
                word_count=(
                    len(chunk.get("words", []))
                    if chunk.get("words")
                    else len(chunk["text"].split())
                ),
            )
            entries.append(entry)

    # Return the complete track
    return SubtitleTrack(metadata=metadata, entries=entries)
