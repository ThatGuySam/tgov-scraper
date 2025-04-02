#!/usr/bin/env python3
"""
Tests for the Government Access Television Meeting Scraper
"""

import asyncio
import json
import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.meetings import fetch_page, parse_meetings, get_tgov_meetings
from src.models.meeting import Meeting


@pytest.fixture
def fixture_path():
    """Path to the fixture file"""
    return Path(__file__).parent / "fixtures" / "tgov_homepage.html"


@pytest.fixture
def real_html(fixture_path):
    """Load the real HTML from the fixture file"""
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def sample_html():
    """Sample HTML fixture with a table of meetings"""
    return """
    <html>
    <body>
        <table class="listingTable">
            <thead>
                <tr>
                    <th>Meeting</th>
                    <th>Date</th>
                    <th>Duration</th>
                    <th>Agenda</th>
                    <th>Video</th>
                </tr>
            </thead>
            <tbody>
                <tr class="listingRow">
                                                                                  <td class="listItem" headers="Name" id="Regular-Council-Meeting" scope="row">
                                                                                        Regular Council Meeting
                                          </td>
                                                                                                                          <td class="listItem" headers="Date Regular-Council-Meeting">
                                                                                          April&nbsp; 2,&nbsp;2025
                                                                                                                                      -
                                                                                               5:03&nbsp;PM
                                                                                                                                    </td>
                                                                                                            <td class="listItem" headers="Duration Regular-Council-Meeting">01h&nbsp;29m</td>
                                                                                                                          <td class="listItem">
                                                                                          <a href="//tulsa-ok.granicus.com/AgendaViewer.php?view_id=4&amp;clip_id=6515" target="_blank">Agenda</a>
                                                                                      </td>
                                                                                                                                                                  <td class="listItem" headers="VideoLink Regular-Council-Meeting">
                                                                                          <a href="javascript:void(0);" onclick="window.open('//tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&amp;clip_id=6515','player','toolbar=no,directories=no,status=yes,scrollbars=yes,resizable=yes,menubar=no')">
                                                                                                  Video
                                                                                              </a>
                                                                                      </td>
                                                                                                                                                                                                      </tr>
                                                                                                                                                                                                      <tr class="listingRow">
                                                                                  <td class="listItem" headers="Name" id="Animal-Welfare-Commission" scope="row">
                                                                                        Animal Welfare Commission
                                          </td>
                                                                                                                          <td class="listItem" headers="Date Animal-Welfare-Commission">
                                                                                          March&nbsp;10,&nbsp;2025
                                                                                                                                      -
                                                                                               6:00&nbsp;PM
                                                                                                                                    </td>
                                                                                                            <td class="listItem" headers="Duration Animal-Welfare-Commission">00h&nbsp;38m</td>
                                                                                                                          <td class="listItem">
                                                                                      </td>
                                                                                                                                                                  <td class="listItem" headers="VideoLink Animal-Welfare-Commission">
                                                                                          <a href="javascript:void(0);" onclick="window.open('//tulsa-ok.granicus.com/MediaPlayer.php?view_id=4&amp;clip_id=6474','player','toolbar=no,directories=no,status=yes,scrollbars=yes,resizable=yes,menubar=no')">
                                                                                                  Video
                                                                                              </a>
                                                                                      </td>
                                                                                                                                                                                                      </tr>
            </tbody>
        </table>
    </body>
    </html>
    """


@pytest.mark.asyncio
async def test_parse_meetings(sample_html):
    """Test that meetings are correctly parsed from HTML"""
    meetings = await parse_meetings(sample_html)

    assert len(meetings) == 2

    assert meetings[0]["meeting"] == "Regular Council Meeting"
    assert meetings[0]["date"] == "April 2, 2025"
    assert meetings[0]["duration"] == "1:29"
    assert "AgendaViewer.php?view_id=4&clip_id=6515" in meetings[0]["agenda"]
    assert "MediaPlayer.php?view_id=4&clip_id=6515" in meetings[0]["video"]

    assert meetings[1]["meeting"] == "Animal Welfare Commission"
    assert meetings[1]["date"] == "March 10, 2025"
    assert meetings[1]["duration"] == "0:38"
    assert meetings[1]["agenda"] is None
    assert "MediaPlayer.php?view_id=4&clip_id=6474" in meetings[1]["video"]


@pytest.mark.asyncio
async def test_parse_real_html(real_html):
    """Test that meetings are correctly parsed from real HTML"""
    meetings = await parse_meetings(real_html)

    # Basic validation
    assert isinstance(meetings, list)
    assert len(meetings) > 0

    # Check that each meeting has the expected fields
    for meeting in meetings:
        assert "meeting" in meeting
        assert "date" in meeting
        assert "duration" in meeting
        # Agenda and video may be None for some meetings


@pytest.mark.asyncio
async def test_fetch_page(real_html):
    """Test that fetch_page correctly fetches HTML content"""
    # Use patch to mock the aiohttp.ClientSession
    with patch("aiohttp.ClientSession") as mock_session_class:
        # Create a mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = real_html

        # Set up the mock session
        mock_session = mock_session_class.return_value
        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Call the function with a new session
        result = await fetch_page("https://test.com", mock_session)

        # Verify the result
        assert result == real_html
        mock_session.get.assert_called_once_with("https://test.com")


@pytest.mark.asyncio
async def test_get_tgov_meetings(real_html):
    """Test that get_tgov_meetings returns a list of Meeting objects"""
    with patch("src.meetings.fetch_page", return_value=real_html):
        meetings = await get_tgov_meetings()

        # Basic validation
        assert isinstance(meetings, list)
        assert len(meetings) > 0

        # Check that each meeting is a Meeting object
        for meeting in meetings:
            assert isinstance(meeting, Meeting)
            assert hasattr(meeting, "meeting")
            assert hasattr(meeting, "date")
            assert hasattr(meeting, "duration")
            assert hasattr(meeting, "clip_id")
            assert hasattr(meeting, "agenda")  # May be None
            assert hasattr(meeting, "video")  # May be None
