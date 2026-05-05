"""Unit tests for fusion module."""

from transcriber.fusion import _group_consecutive


class TestGroupConsecutive:
    def test_same_speaker_small_gap_is_merged(self):
        segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
            {"start": 2.3, "end": 4.0, "speaker": "SPEAKER_00"},
        ]
        result = _group_consecutive(segments, gap_threshold=0.5)
        assert len(result) == 1
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 4.0

    def test_different_speakers_not_merged(self):
        segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
            {"start": 2.1, "end": 4.0, "speaker": "SPEAKER_01"},
        ]
        result = _group_consecutive(segments)
        assert len(result) == 2

    def test_same_speaker_large_gap_not_merged(self):
        segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 7.0, "speaker": "SPEAKER_00"},
        ]
        result = _group_consecutive(segments, gap_threshold=0.5)
        assert len(result) == 2

    def test_empty_input(self):
        assert _group_consecutive([]) == []
