"""Unit tests for identity module."""

from transcriber.identity import apply_speaker_map, build_speaker_map


class TestBuildSpeakerMap:
    def _make_segments(self):
        return [
            {"start": 0.0,  "end": 10.0, "speaker": "SPEAKER_00"},  # 10s
            {"start": 10.0, "end": 16.0, "speaker": "SPEAKER_01"},  # 6s
            {"start": 16.0, "end": 19.0, "speaker": "SPEAKER_02"},  # 3s
        ]

    def test_names_assigned_by_talk_time(self):
        segments = self._make_segments()
        speaker_map = build_speaker_map(segments, ["Alice", "Bob", "Chloe"])
        assert speaker_map["SPEAKER_00"] == "Alice"
        assert speaker_map["SPEAKER_01"] == "Bob"
        assert speaker_map["SPEAKER_02"] == "Chloe"

    def test_fewer_names_than_speakers(self):
        segments = self._make_segments()
        speaker_map = build_speaker_map(segments, ["Alice"])
        assert speaker_map["SPEAKER_00"] == "Alice"
        assert speaker_map["SPEAKER_01"] == "SPEAKER_01"

    def test_no_names_returns_ids(self):
        segments = self._make_segments()
        speaker_map = build_speaker_map(segments, [])
        for spk in ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]:
            assert speaker_map[spk] == spk

    def test_no_duplicate_names(self):
        segments = self._make_segments()
        speaker_map = build_speaker_map(segments, ["Alice", "Bob", "Chloe"])
        names = list(speaker_map.values())
        assert len(names) == len(set(names))


class TestApplySpeakerMap:
    def test_names_applied_to_segments(self):
        segments = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Bonjour"}]
        result = apply_speaker_map(segments, {"SPEAKER_00": "Alice"})
        assert result[0]["speaker"] == "Alice"

    def test_unknown_speaker_kept_as_is(self):
        segments = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_99", "text": "Test"}]
        result = apply_speaker_map(segments, {"SPEAKER_00": "Alice"})
        assert result[0]["speaker"] == "SPEAKER_99"
