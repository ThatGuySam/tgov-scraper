"""
Subtitle Models Module

Contains all Pydantic models for subtitle track formats (SRT, ASS, VTT)
and transcript data structures.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator


class TrackFormat(str, Enum):
    """Format of the subtitle track."""

    SRT = "srt"
    ASS = "ass"
    VTT = "vtt"


class SpeakerInfo(BaseModel):
    """Information about a speaker in the subtitle track."""

    id: str
    color: str
    display_name: Optional[str] = None


class SubtitleTimestamp(BaseModel):
    """Base model for subtitle timestamps."""

    start: float
    end: float

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        """Validate that end time comes after start time."""
        if "start" in info.data and v < info.data["start"]:
            raise ValueError("End time must be after start time")
        return v

    def duration(self) -> float:
        """Calculate duration of this subtitle."""
        return self.end - self.start


class BaseSubtitleEntry(SubtitleTimestamp):
    """Base model for a subtitle entry."""

    text: str
    speaker_id: Optional[str] = None
    index: Optional[int] = None
    word_count: Optional[int] = None


class SrtEntry(BaseSubtitleEntry):
    """Model for an SRT subtitle entry."""

    def format(self) -> str:
        """Format the entry as an SRT subtitle block."""
        from src.subtitles import format_time_for_srt

        return (
            f"{self.index}\n"
            f"{format_time_for_srt(self.start)} --> {format_time_for_srt(self.end)}\n"
            f"{self.text}\n\n"
        )


class VttEntry(BaseSubtitleEntry):
    """Model for a VTT subtitle entry."""

    def format(self) -> str:
        """Format the entry as a VTT subtitle block."""
        from src.subtitles import format_time_for_vtt

        cue_id = str(self.index) if self.index is not None else ""
        return (
            f"{cue_id}\n"
            f"{format_time_for_vtt(self.start)} --> {format_time_for_vtt(self.end)}\n"
            f"{self.text}\n\n"
        )


class AssStyle(BaseModel):
    """Style information for ASS subtitles."""

    font_name: str = "Arial"
    font_size: int = 24
    primary_color: str = "FFFFFF"  # Text color (BGR format)
    secondary_color: str = "FFFFFF"  # Secondary color
    outline_color: str = "000000"  # Outline color
    back_color: str = "000000"  # Shadow/background color
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike_out: bool = False
    scale_x: int = 100
    scale_y: int = 100
    spacing: int = 0
    angle: int = 0
    border_style: int = 1
    outline: int = 1
    shadow: int = 0
    alignment: int = 2  # 2 = bottom center
    margin_l: int = 10
    margin_r: int = 10
    margin_v: int = 20
    encoding: int = 1


class AssEntry(BaseSubtitleEntry):
    """Model for an ASS subtitle entry."""

    layer: int = 0
    style: str = "Default"
    name: str = ""
    margin_l: int = 0
    margin_r: int = 0
    margin_v: int = 0
    effect: str = ""
    styled_text: Optional[str] = None

    def format(self) -> str:
        """Format the entry as an ASS dialogue line."""
        from src.subtitles import format_time_for_ass

        text = self.styled_text if self.styled_text else self.text
        start_time = format_time_for_ass(self.start)
        end_time = format_time_for_ass(self.end)

        return (
            f"Dialogue: {self.layer},{start_time},{end_time},{self.style},"
            f"{self.name},{self.margin_l},{self.margin_r},{self.margin_v},"
            f"{self.effect},{text}\n"
        )


class TrackMetadata(BaseModel):
    """Metadata for a subtitle track."""

    format: TrackFormat
    language: str = "en"
    title: Optional[str] = None
    speakers: Dict[str, SpeakerInfo] = Field(default_factory=dict)
    style: Optional[AssStyle] = None
    created_at: Optional[str] = None
    source_file: Optional[str] = None
    word_count: Optional[int] = None
    duration: Optional[float] = None


class SubtitleTrack(BaseModel):
    """Complete subtitle track with metadata and entries."""

    metadata: TrackMetadata
    entries: List[Union[SrtEntry, VttEntry, AssEntry]]

    def to_srt_content(self) -> str:
        """Convert track to SRT format string."""
        if not all(isinstance(entry, SrtEntry) for entry in self.entries):
            raise ValueError("All entries must be SrtEntry objects")

        return "".join(entry.format() for entry in self.entries)

    def to_vtt_content(self) -> str:
        """Convert track to VTT format string."""
        if not all(isinstance(entry, VttEntry) for entry in self.entries):
            raise ValueError("All entries must be VttEntry objects")

        return "WEBVTT\n\n" + "".join(entry.format() for entry in self.entries)

    def to_ass_content(self) -> str:
        """Convert track to ASS format string."""
        from src.subtitles import get_color_code_for_ass

        if not all(isinstance(entry, AssEntry) for entry in self.entries):
            raise ValueError("All entries must be AssEntry objects")

        style = self.metadata.style or AssStyle()

        # Create ASS header
        header = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: 384",
            f"PlayResY: 288",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        ]

        # Add default style
        header.append(
            f"Style: Default,{style.font_name},{style.font_size},&H00{style.primary_color},&H00{style.secondary_color},"
            f"&H00{style.outline_color},&H{format(int(0.5 * 255), '02x')}{style.back_color},"
            f"{1 if style.bold else 0},{1 if style.italic else 0},{1 if style.underline else 0},{1 if style.strike_out else 0},"
            f"{style.scale_x},{style.scale_y},{style.spacing},{style.angle},{style.border_style},{style.outline},{style.shadow},"
            f"{style.alignment},{style.margin_l},{style.margin_r},{style.margin_v},{style.encoding}"
        )

        # Add speaker-specific styles
        for speaker_id, info in self.metadata.speakers.items():
            color_code = info.color
            if not re.match(r"^[0-9A-F]{6}$", color_code, re.IGNORECASE):
                color_code = get_color_code_for_ass(color_code)

            style_name = f"Speaker_{speaker_id.replace('SPEAKER_', '')}"
            header.append(
                f"Style: {style_name},{style.font_name},{style.font_size},&H00{color_code},&H00{style.secondary_color},"
                f"&H00{style.outline_color},&H{format(int(0.5 * 255), '02x')}{style.back_color},"
                f"{1 if style.bold else 0},{1 if style.italic else 0},{1 if style.underline else 0},{1 if style.strike_out else 0},"
                f"{style.scale_x},{style.scale_y},{style.spacing},{style.angle},{style.border_style},{style.outline},{style.shadow},"
                f"{style.alignment},{style.margin_l},{style.margin_r},{style.margin_v},{style.encoding}"
            )

        header.append("")
        header.append("[Events]")
        header.append(
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        )
        header.append("")

        # Add all dialogue lines
        content = (
            "\n".join(header) + "\n" + "".join(entry.format() for entry in self.entries)
        )
        return content

    def content(self) -> str:
        """
        Generate content string based on track format.

        Returns:
            Formatted subtitle content string based on the track's format.
        """
        if self.metadata.format == TrackFormat.SRT:
            return self.to_srt_content()
        elif self.metadata.format == TrackFormat.VTT:
            return self.to_vtt_content()
        elif self.metadata.format == TrackFormat.ASS:
            return self.to_ass_content()
        else:
            raise ValueError(f"Unsupported track format: {self.metadata.format}")


class Word(BaseModel):
    """Model for a word in the transcript with timing information."""

    word: str
    start: float
    end: float
    speaker: Optional[str] = None
    probability: Optional[float] = None


class TranscriptSegment(BaseModel):
    """Model for a segment in the transcript."""

    id: Optional[int] = None
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[Word]] = None


class Transcript(BaseModel):
    """Model for a complete transcript."""

    language: str = "en"
    segments: List[TranscriptSegment]
