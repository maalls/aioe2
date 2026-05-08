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


def test_viewer_panel_script_registers_htmx_module(folder_data):
    """viewer-panel-interactions must register itself in window.__htmxModules."""
    html = _render(folder_data)
    assert "__htmxModules" in html
    assert "'viewer-panel-interactions'" in html


def test_viewer_panel_script_destroys_previous_instance(folder_data):
    """Script must call destroy() on any existing module before re-init."""
    html = _render(folder_data)
    assert "_modules['viewer-panel-interactions'].destroy()" in html


def test_viewer_panel_script_removes_beforeunload_on_destroy(folder_data):
    """destroy() must remove the beforeunload listener to prevent accumulation."""
    html = _render(folder_data)
    assert "removeEventListener('beforeunload'" in html
    assert "_beforeUnloadHandler" in html


def test_segments_table_script_registers_htmx_module(folder_data):
    """segments-table-interactions must register itself in window.__htmxModules."""
    html = _render(folder_data)
    assert "'segments-table-interactions'" in html


def test_segments_table_script_destroys_previous_instance(folder_data):
    """Script must call destroy() on any existing module before re-init."""
    html = _render(folder_data)
    assert "_modules['segments-table-interactions'].destroy()" in html
