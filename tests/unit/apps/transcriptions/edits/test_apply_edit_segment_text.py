import pytest
from apps.transcriptions.edits import apply_edit_segment_text, segment_key


def test_updates_text(sample_state):
    seg = sample_state["segments"][0]
    key = segment_key(seg)
    updated = apply_edit_segment_text(sample_state, key, "Texte corrigé")
    assert updated["segments"][0]["text"] == "Texte corrigé"


def test_does_not_mutate_input(sample_state):
    seg = sample_state["segments"][0]
    key = segment_key(seg)
    original_text = seg["text"]
    apply_edit_segment_text(sample_state, key, "Texte corrigé")
    assert sample_state["segments"][0]["text"] == original_text


def test_unknown_key_raises(sample_state):
    with pytest.raises(KeyError):
        apply_edit_segment_text(sample_state, "0000000000000000", "Texte")
