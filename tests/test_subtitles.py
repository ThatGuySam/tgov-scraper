#!/usr/bin/env python
"""
Tests for the subtitles module.
"""
import pytest
from pathlib import Path
from src.subtitles import (
    create_track,
    format_time_for_srt,
    format_time_for_vtt,
    format_time_for_ass,
    load_transcript,
    chunk_transcript,
)
from src.models.subtitles import (
    TrackFormat,
    SrtEntry,
    VttEntry,
    AssEntry,
    Transcript,
    TranscriptSegment,
    Word,
)


@pytest.fixture
def fixture_transcript_path() -> Path:
    """Fixture for the path to our mock transcript fixture."""
    return Path("tests/fixtures/mock_transcript.diarized.json")


@pytest.fixture
def fixture_transcript(fixture_transcript_path) -> Transcript:
    """Load the transcript fixture."""
    return load_transcript(fixture_transcript_path)


def test_format_time_for_srt():
    """Test SRT timestamp formatting."""
    assert format_time_for_srt(0) == "00:00:00,000"
    assert format_time_for_srt(3661.5) == "01:01:01,500"
    assert format_time_for_srt(123.456) == "00:02:03,456"


def test_format_time_for_vtt():
    """Test VTT timestamp formatting."""
    assert format_time_for_vtt(0) == "00:00:00.000"
    assert format_time_for_vtt(3661.5) == "01:01:01.500"
    assert format_time_for_vtt(123.456) == "00:02:03.456"


def test_format_time_for_ass():
    """Test ASS timestamp formatting."""
    assert format_time_for_ass(0) == "0:00:00.00"
    assert format_time_for_ass(3661.5) == "1:01:01.50"
    assert format_time_for_ass(123.456) == "0:02:03.45"


def test_create_srt_track(fixture_transcript_path):
    """Test creating an SRT track from a transcript."""
    srt_track = create_track(
        fixture_transcript_path,
        format="srt",
        max_duration=5.0,
        max_words=14,
        include_speaker_prefix=True,
    )

    # Verify track metadata
    assert srt_track.metadata.format == TrackFormat.SRT
    assert srt_track.metadata.language == "en"

    # Verify that entries were created
    assert len(srt_track.entries) > 0
    assert all(isinstance(entry, SrtEntry) for entry in srt_track.entries)

    # Check that speaker prefixes were added
    assert any("[Speaker" in entry.text for entry in srt_track.entries)

    # Test content generation using unified method
    srt_content = srt_track.content()
    assert srt_content.startswith("1\n")
    assert "-->" in srt_content

    # Verify old method still works for backward compatibility
    assert srt_track.to_srt_content() == srt_content


def test_create_vtt_track(fixture_transcript_path):
    """Test creating a VTT track from a transcript."""
    vtt_track = create_track(
        fixture_transcript_path,
        format="vtt",
        max_duration=4.0,
        max_words=12,
    )

    # Verify track metadata
    assert vtt_track.metadata.format == TrackFormat.VTT
    assert vtt_track.metadata.language == "en"

    # Verify that entries were created
    assert len(vtt_track.entries) > 0
    assert all(isinstance(entry, VttEntry) for entry in vtt_track.entries)

    # Test content generation using unified method
    vtt_content = vtt_track.content()
    assert vtt_content.startswith("WEBVTT")
    assert "-->" in vtt_content

    # Verify old method still works for backward compatibility
    assert vtt_track.to_vtt_content() == vtt_content


def test_create_ass_track(fixture_transcript_path):
    """Test creating an ASS track from a transcript."""
    ass_track = create_track(
        fixture_transcript_path,
        format="ass",
        font_size=28,
        bg_opacity=0.3,
    )

    # Verify track metadata
    assert ass_track.metadata.format == TrackFormat.ASS
    assert ass_track.metadata.language == "en"
    assert ass_track.metadata.style.font_size == 28

    # Verify that entries were created
    assert len(ass_track.entries) > 0
    assert all(isinstance(entry, AssEntry) for entry in ass_track.entries)

    # Test content generation using unified method
    ass_content = ass_track.content()
    assert "[Script Info]" in ass_content
    assert "Dialogue:" in ass_content

    # Verify old method still works for backward compatibility
    assert ass_track.to_ass_content() == ass_content


def test_load_transcript(fixture_transcript_path):
    """Test that a transcript can be loaded from a JSON file."""
    transcript = load_transcript(fixture_transcript_path)
    assert transcript.language == "en"
    assert len(transcript.segments) > 0

    # Test at least one speaker from our fixture
    speakers = set(
        segment.speaker for segment in transcript.segments if segment.speaker
    )
    assert "SPEAKER_01" in speakers
    assert "SPEAKER_02" in speakers


def test_chunk_transcript(fixture_transcript):
    """Test the transcript chunking functionality."""
    chunks = chunk_transcript(
        fixture_transcript,
        max_duration=5.0,
        max_length=80,
        max_words=14,
        min_duration=0.5,
    )

    # Verify chunks were created
    assert len(chunks) > 0

    # Check chunk properties
    for chunk in chunks:
        assert "start" in chunk
        assert "end" in chunk
        assert "text" in chunk
        assert "speaker" in chunk
        if chunk["start"] != chunk["end"]:  # Skip zero-duration chunks
            assert chunk["end"] - chunk["start"] >= 0.5  # min_duration
        assert len(chunk["text"]) <= 80  # max_length
