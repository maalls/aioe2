from .conftest import render


def test_edit_inline_script_module_present(folder_data):
    """_edit_inline_scripts.html must be included in the table."""
    html = render(folder_data)
    assert 'data-module="edit-inline-interactions"' in html


def test_edit_inline_registers_app_edits(folder_data):
    """window.appEdits must be defined by the module."""
    html = render(folder_data)
    assert "window.appEdits" in html


def test_edit_inline_exposes_save_methods(folder_data):
    """appEdits must expose all four save methods."""
    html = render(folder_data)
    assert "saveSegmentText" in html
    assert "saveSpeaker" in html
    assert "saveTopic" in html
    assert "saveSubtopic" in html
