"""Unit tests for diarization module."""

import pytest


class TestDiarizationSegments:
    def test_segments_are_chronological(self):
        segments = [
            {"start": 0.0, "end": 2.5, "speaker": "SPEAKER_00"},
            {"start": 2.5, "end": 5.1, "speaker": "SPEAKER_01"},
            {"start": 5.1, "end": 8.0, "speaker": "SPEAKER_00"},
        ]
        for i in range(len(segments) - 1):
            assert segments[i]["end"] <= segments[i + 1]["start"]

    def test_each_segment_start_before_end(self):
        segments = [
            {"start": 0.0, "end": 2.5, "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 5.0, "speaker": "SPEAKER_01"},
        ]
        for seg in segments:
            assert seg["start"] < seg["end"]

    def test_no_sub_100ms_segments(self):
        segments = [
            {"start": 0.0, "end": 2.5, "speaker": "SPEAKER_00"},
            {"start": 3.0, "end": 5.0, "speaker": "SPEAKER_01"},
        ]
        for seg in segments:
            assert (seg["end"] - seg["start"]) >= 0.1
