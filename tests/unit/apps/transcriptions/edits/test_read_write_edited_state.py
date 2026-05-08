from apps.transcriptions.edits import build_edited_state, read_edited_state, write_edited_state
from .conftest import SOURCE_SEGMENTS, SOURCE_TIMELINE


def test_returns_none_when_absent(tmp_folder):
    assert read_edited_state(tmp_folder) is None


def test_roundtrip(tmp_folder):
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    write_edited_state(tmp_folder, state)
    loaded = read_edited_state(tmp_folder)
    assert loaded["speaker_map"] == state["speaker_map"]
    assert len(loaded["segments"]) == len(state["segments"])
    assert len(loaded["chapters"]) == len(state["chapters"])


def test_creates_file(tmp_folder):
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    write_edited_state(tmp_folder, state)
    assert (tmp_folder / "edited.json").exists()
