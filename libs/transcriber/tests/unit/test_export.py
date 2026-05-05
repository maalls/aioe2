"""Unit tests for export module."""

import json

from transcriber.export import to_json, to_srt, to_txt

SAMPLE_SEGMENTS = [
    {"start": 0.0,  "end": 4.5,  "speaker": "Alice", "text": "Bonjour à tous."},
    {"start": 4.8,  "end": 9.2,  "speaker": "Bob",   "text": "Merci Alice."},
    {"start": 9.5,  "end": 15.0, "speaker": "Alice", "text": "On commence."},
]


class TestToJson:
    def test_file_is_created(self, tmp_path):
        out = tmp_path / "result.json"
        to_json({"segments": SAMPLE_SEGMENTS}, out)
        assert out.exists()

    def test_content_is_valid_json(self, tmp_path):
        out = tmp_path / "result.json"
        to_json({"segments": SAMPLE_SEGMENTS}, out)
        data = json.loads(out.read_text())
        assert "segments" in data

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "subdir" / "result.json"
        to_json({}, out)
        assert out.exists()


class TestToTxt:
    def test_file_is_created(self, tmp_path):
        out = tmp_path / "result.txt"
        to_txt(SAMPLE_SEGMENTS, out)
        assert out.exists()

    def test_contains_all_speakers(self, tmp_path):
        out = tmp_path / "result.txt"
        to_txt(SAMPLE_SEGMENTS, out)
        content = out.read_text()
        assert "Alice" in content
        assert "Bob" in content

    def test_contains_timestamps(self, tmp_path):
        out = tmp_path / "result.txt"
        to_txt(SAMPLE_SEGMENTS, out)
        content = out.read_text()
        assert "[" in content and "]" in content


class TestToSrt:
    def test_file_is_created(self, tmp_path):
        out = tmp_path / "result.srt"
        to_srt(SAMPLE_SEGMENTS, out)
        assert out.exists()

    def test_sequential_numbering(self, tmp_path):
        out = tmp_path / "result.srt"
        to_srt(SAMPLE_SEGMENTS, out)
        lines = out.read_text().split("\n")
        assert lines[0] == "1"
        # Find second block (after blank line)
        second_block_start = next(i for i, l in enumerate(lines[2:], 2) if l == "2")
        assert lines[second_block_start] == "2"

    def test_srt_timecode_format(self, tmp_path):
        out = tmp_path / "result.srt"
        to_srt(SAMPLE_SEGMENTS, out)
        content = out.read_text()
        assert "-->" in content
        # HH:MM:SS,mmm format
        import re
        assert re.search(r"\d{2}:\d{2}:\d{2},\d{3}", content)
