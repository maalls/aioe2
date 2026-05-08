from django.template.loader import render_to_string


def test_render_app_ui_bootstrap_module():
    html = render_to_string(
        "transcriptions/browser.html",
        {
            "selected_folder": "folder-a",
            "folders": [],
            "folder_data": {
                "folder_name": "folder-a",
                "timeline_groups": [],
                "speakers_found": 0,
                "audio_duration_pretty": "0s",
                "segments": [],
                "speaker_map": {},
                "preview_audio_file": "",
                "preview_video_file": "",
                "preview_vtt_file": "",
                "timeline_file": "",
                "txt_file": "",
                "srt_file": "",
            },
        },
    )

    assert 'data-module="app-ui-bootstrap"' in html
    assert 'window.appUi = window.appUi || {}' in html
