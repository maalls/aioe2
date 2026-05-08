from django.template.loader import render_to_string


def test_render_modular_components_for_audio(folder_data):
    html = render_to_string(
        "transcriptions/_viewer_panel.html",
        {
            "selected_folder": "folder-a",
            "folders": [{"name": "folder-a"}, {"name": "folder-b"}],
            "folder_data": folder_data,
        },
    )

    assert 'data-component="folder-selector"' in html
    assert 'data-component="media-player"' in html
    assert 'data-component="timeline-controls"' in html
    assert 'data-module="viewer-panel-interactions"' in html
    assert 'data-module="segments-table-interactions"' in html
