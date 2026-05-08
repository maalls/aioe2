from django.template.loader import render_to_string


def test_render_no_media_message(folder_data):
    folder_data["preview_audio_file"] = ""

    html = render_to_string(
        "transcriptions/_viewer_panel.html",
        {
            "selected_folder": "folder-a",
            "folders": [{"name": "folder-a"}],
            "folder_data": folder_data,
        },
    )

    assert 'data-component="media-player"' in html
    assert 'Assets média non disponibles pour ce dossier.' in html
