from django.template.loader import render_to_string


def test_render_error_channel_bindings():
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

    assert '@htmx:responseError.window="errorMessage = ' in html
    assert '@htmx:sendError.window="errorMessage = ' in html
    assert '@app:ajax-error.window="errorMessage = ' in html
