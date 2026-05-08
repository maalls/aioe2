import pytest
from apps.transcriptions.edits import apply_rename_topic


def test_updates_title(sample_state):
    updated = apply_rename_topic(sample_state, 1, "Nouveau titre")
    assert updated["chapters"][0]["title"] == "Nouveau titre"


def test_does_not_mutate_input(sample_state):
    apply_rename_topic(sample_state, 1, "Nouveau titre")
    assert sample_state["chapters"][0]["title"] == "Introduction"


def test_invalid_index_raises(sample_state):
    with pytest.raises(IndexError):
        apply_rename_topic(sample_state, 99, "Titre")
