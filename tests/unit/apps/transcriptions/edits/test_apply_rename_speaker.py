import pytest
from apps.transcriptions.edits import apply_rename_speaker


def test_updates_speaker_map(sample_state):
    updated = apply_rename_speaker(sample_state, "SPEAKER_00", "Alison")
    assert updated["speaker_map"]["SPEAKER_00"] == "Alison"


def test_does_not_mutate_input(sample_state):
    apply_rename_speaker(sample_state, "SPEAKER_00", "Alison")
    assert sample_state["speaker_map"]["SPEAKER_00"] == "Alice"


def test_unknown_id_raises(sample_state):
    with pytest.raises(KeyError):
        apply_rename_speaker(sample_state, "SPEAKER_99", "Nobody")


def test_keeps_other_speakers(sample_state):
    updated = apply_rename_speaker(sample_state, "SPEAKER_00", "Alison")
    assert updated["speaker_map"]["SPEAKER_01"] == "Bob"
