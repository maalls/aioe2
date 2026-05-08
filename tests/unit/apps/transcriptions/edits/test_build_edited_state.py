from apps.transcriptions.edits import build_edited_state
from .conftest import SOURCE_SEGMENTS, SOURCE_TIMELINE


def test_has_expected_keys():
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    assert set(state.keys()) == {"segments", "speaker_map", "chapters"}


def test_segments():
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    assert len(state["segments"]) == 4
    assert state["segments"][0]["text"] == "Bonjour tout le monde"


def test_speaker_map():
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    assert state["speaker_map"] == {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}


def test_chapters():
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    assert len(state["chapters"]) == 2
    assert state["chapters"][0]["title"] == "Introduction"


def test_is_deep_copy():
    state = build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
    state["segments"][0]["text"] = "MUTATED"
    assert SOURCE_SEGMENTS["segments"][0]["text"] == "Bonjour tout le monde"
