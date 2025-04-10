#!/usr/bin/env python
"""
Tests for the subtitles module.
"""
import pytest
from pathlib import Path
from src.subtitles import (
    create_subtitles,
    format_time_for_vtt,
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


def load_transcript(fixture_transcript_path) -> Transcript:
    """Load the transcript fixture."""
    with open(fixture_transcript_path, "r") as f:
        transcript_data = f.read()
    transcript = Transcript.model_validate_json(transcript_data)
    return transcript


@pytest.fixture
def fixture_transcript_path() -> Path:
    """Fixture for the path to our mock transcript fixture."""
    return Path("tests/fixtures/mock_transcript.diarized.json")


@pytest.fixture
def fixture_transcript(fixture_transcript_path) -> Transcript:
    return load_transcript(fixture_transcript_path)


def test_create_vtt_track(fixture_transcript):
    """Test creating a VTT track from a transcript."""
    vtt_track = create_subtitles(
        fixture_transcript,
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


def test_chunk_transcript(fixture_transcript):
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
