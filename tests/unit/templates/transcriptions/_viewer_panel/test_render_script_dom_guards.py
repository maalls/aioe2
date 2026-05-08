from django.template.loader import render_to_string


def _render(folder_data):
    return render_to_string(
        "transcriptions/_viewer_panel.html",
        {
            "selected_folder": "folder-a",
            "folders": [{"name": "folder-a"}, {"name": "folder-b"}],
            "folder_data": folder_data,
        },
    )


def test_viewer_script_uses_viewer_panel_root_scope(folder_data):
    html = _render(folder_data)
    assert "panelRoot" in html
    assert "panelRoot.querySelector('#preview-player')" in html


def test_viewer_script_guards_history_replace_state(folder_data):
    html = _render(folder_data)
    assert "typeof history !== 'undefined'" in html
    assert "typeof history.replaceState === 'function'" in html


def test_segments_script_requires_sync_root(folder_data):
    html = _render(folder_data)
    assert "if (!player || !syncRoot) return;" in html


def test_segments_script_guards_non_finite_player_time(folder_data):
    html = _render(folder_data)
    assert "if (!Number.isFinite(t))" in html
