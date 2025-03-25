#!/usr/bin/env python3
"""
VTT Subtitles Module

This module provides functions for converting transcripts to WebVTT subtitle format.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


def format_timestamp(seconds: float) -> str:
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

    return f"{hours:02d}:{minutes:02d}:{seconds_remainder:06.3f}".replace(".", ",")


def chunk_transcript(
    segments: List[Dict[str, Any]],
    max_duration: float = 5.0,
    max_length: int = 80,
    min_duration: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Chunk transcript segments into appropriate subtitle-sized chunks

    Args:
        segments: List of transcript segments with start, end, and text fields
        max_duration: Maximum duration in seconds for a subtitle
        max_length: Maximum character length for a subtitle line
        min_duration: Minimum duration in seconds for a subtitle

    Returns:
        List of chunked subtitle objects with start, end, and text
    """
    chunks = []
    current_chunk = {"text": "", "start": 0, "end": 0, "speaker": ""}

    for segment in segments:
        # Skip very short segments
        if segment["end"] - segment["start"] < 0.1:
            continue

        # If the segment is too long, split it by individual sentences or phrases
        if (
            segment["end"] - segment["start"] > max_duration
            or len(segment["text"]) > max_length
        ):
            # Set the start time for the first chunk if we don't have one
            if not current_chunk["text"]:
                current_chunk["start"] = segment["start"]
                current_chunk["speaker"] = segment.get("speaker", "")

            # Split text by punctuation or use words if needed
            text_parts = []

            # First try to split by punctuation
            parts = (
                segment["text"]
                .replace(".", ".|")
                .replace("?", "?|")
                .replace("!", "!|")
                .replace(",", ",|")
                .split("|")
            )

            # If that didn't work well, fall back to chunking by words for length
            if len(parts) <= 1:
                words = segment["text"].split()
                current_part = []

                for word in words:
                    current_part.append(word)
                    if len(" ".join(current_part)) > max_length:
                        if len(current_part) > 1:
                            current_part.pop()  # Remove the last word that exceeded the limit
                            text_parts.append(" ".join(current_part))
                            current_part = [word]
                        else:
                            text_parts.append(word)
                            current_part = []

                if current_part:
                    text_parts.append(" ".join(current_part))
            else:
                # Use the punctuation-based splitting
                current_text = ""
                for part in parts:
                    if not part:
                        continue
                    if len(current_text + part) > max_length:
                        if current_text:
                            text_parts.append(current_text.strip())
                        current_text = part
                    else:
                        current_text += part

                if current_text:
                    text_parts.append(current_text.strip())

            # Calculate approximate timestamps for each part
            total_duration = segment["end"] - segment["start"]
            for i, part in enumerate(text_parts):
                if not part.strip():
                    continue

                # Calculate a proportional timestamp based on text length
                part_length = len(part)
                segment_length = len(segment["text"])
                part_duration = (
                    total_duration * (part_length / segment_length)
                    if segment_length > 0
                    else min_duration
                )

                if i == 0:
                    part_start = segment["start"]
                else:
                    part_start = chunks[-1]["end"] if chunks else segment["start"]

                part_end = min(part_start + part_duration, segment["end"])

                # Ensure minimum duration
                if part_end - part_start < min_duration:
                    part_end = part_start + min_duration

                chunks.append(
                    {
                        "start": part_start,
                        "end": part_end,
                        "text": part.strip(),
                        "speaker": segment.get("speaker", ""),
                    }
                )
        else:
            # The segment is an appropriate length, use it directly
            chunks.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "speaker": segment.get("speaker", ""),
                }
            )

    return chunks


def create_vtt_from_diarized_json(
    json_file: Path,
    output_file: Optional[Path] = None,
    include_speaker: bool = True,
    max_duration: float = 5.0,
    max_length: int = 80,
) -> str:
    """
    Create WebVTT subtitles from a diarized JSON transcript file

    Args:
        json_file: Path to the JSON transcript file
        output_file: Path where the VTT file should be saved (optional)
        include_speaker: Whether to include speaker labels in the subtitles
        max_duration: Maximum duration for each subtitle
        max_length: Maximum text length for each subtitle

    Returns:
        The VTT file content as a string
    """
    # Load the JSON file
    with open(json_file, "r") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    if not segments:
        logging.warning(f"No segments found in {json_file}")
        return ""

    # Chunk the transcript into subtitle-sized pieces
    chunks = chunk_transcript(segments, max_duration, max_length)

    # Generate the VTT content
    vtt_content = ["WEBVTT", ""]

    for i, chunk in enumerate(chunks):
        # Add cue identifier (optional)
        vtt_content.append(f"{i+1}")

        # Add timestamp
        start_time = format_timestamp(chunk["start"])
        end_time = format_timestamp(chunk["end"])
        vtt_content.append(f"{start_time} --> {end_time}")

        # Add text, optionally with speaker label
        text = chunk["text"]
        if include_speaker and chunk.get("speaker"):
            speaker_label = chunk["speaker"].replace("SPEAKER_", "Speaker ")
            text = f"<v {speaker_label}>{text}</v>"

        vtt_content.append(text)
        vtt_content.append("")  # Empty line between cues

    # Join the lines
    vtt_content_str = "\n".join(vtt_content)

    # Optionally save to file
    if output_file:
        with open(output_file, "w") as f:
            f.write(vtt_content_str)
        logging.info(f"VTT file saved to {output_file}")

    return vtt_content_str
