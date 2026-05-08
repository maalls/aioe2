from .conftest import render


def test_topic_title_has_edit_url(folder_data):
    """Topic title must embed its edit URL via x-data."""
    html = render(folder_data)
    assert "transcription-edit-topic-rename" in html or "/edit/folder-a/topic/1/rename" in html


def test_topic_title_has_dblclick_trigger(folder_data):
    """Topic title must activate edit mode on double-click."""
    html = render(folder_data)
    assert "dblclick" in html
    assert "topicInp" in html


def test_subtopic_title_has_edit_url(folder_data):
    """Subtopic title must embed its edit URL via x-data."""
    html = render(folder_data)
    assert "/edit/folder-a/subtopic/1.1/rename" in html


def test_subtopic_title_has_dblclick_trigger(folder_data):
    """Subtopic title must activate edit mode on double-click."""
    html = render(folder_data)
    assert "subInp" in html
