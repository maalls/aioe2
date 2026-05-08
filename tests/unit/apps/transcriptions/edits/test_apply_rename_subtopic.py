import pytest
from apps.transcriptions.edits import apply_rename_subtopic


def test_updates_title(sample_state):
    updated = apply_rename_subtopic(sample_state, 1, 1, "Nouvel accueil")
    assert updated["chapters"][0]["analysis"]["sub_topics"][0]["title"] == "Nouvel accueil"


def test_does_not_mutate_input(sample_state):
    apply_rename_subtopic(sample_state, 1, 1, "Nouvel accueil")
    assert sample_state["chapters"][0]["analysis"]["sub_topics"][0]["title"] == "Accueil"


def test_invalid_topic_raises(sample_state):
    with pytest.raises(IndexError):
        apply_rename_subtopic(sample_state, 99, 1, "Titre")


def test_invalid_subtopic_raises(sample_state):
    with pytest.raises(IndexError):
        apply_rename_subtopic(sample_state, 1, 99, "Titre")
