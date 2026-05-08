from .conftest import render


def test_segment_speaker_label_has_edit_url(folder_data):
    """Speaker label must embed the speaker rename URL via x-data."""
    html = render(folder_data)
    assert "/edit/folder-a/speaker/SPEAKER_00/rename" in html


def test_segment_speaker_label_has_dblclick_trigger(folder_data):
    """Speaker label must activate edit mode on double-click."""
    html = render(folder_data)
    assert "spkInp" in html


def test_segment_text_has_edit_url(folder_data):
    """Segment text must embed the text edit URL via x-data."""
    html = render(folder_data)
    assert "/edit/folder-a/segment/abc123/text" in html


def test_segment_text_has_dblclick_trigger(folder_data):
    """Segment text must activate edit mode on double-click."""
    html = render(folder_data)
    assert "txtInp" in html


def test_segment_text_uses_textarea(folder_data):
    """Segment text edit must use a textarea (multi-line)."""
    html = render(folder_data)
    assert "<textarea" in html
