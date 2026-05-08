import copy

import pytest


@pytest.fixture()
def folder_data():
    return {
        "folder_name": "folder-a",
        "speakers_found": 2,
        "audio_duration_pretty": "1m 20s",
        "segments": [],
        "speaker_map": {"SPEAKER_00": "Alice"},
        "timeline_file": "source.timeline.deep.json",
        "timeline_groups": [
            {
                "index": 1,
                "title": "Intro",
                "range_pretty": "0:00 - 0:10",
                "summary": "",
                "sub_topics": [
                    {
                        "index": 1,
                        "title": "Accueil",
                        "range_pretty": "0:00 - 0:10",
                        "summary": "",
                        "segments": [
                            {
                                "start": 0.0,
                                "end": 2.0,
                                "start_pretty": "0:00",
                                "speaker": "SPEAKER_00",
                                "speaker_label": "Alice",
                                "text": "Bonjour tout le monde",
                                "segment_key": "abc123",
                                "is_bookmarked": False,
                                "out_of_topic": False,
                            }
                        ],
                    }
                ],
                "other_segments": [],
            }
        ],
        "preview_audio_file": "audio.preview.mp3",
        "preview_video_file": "",
        "preview_vtt_file": "",
        "txt_file": "out.txt",
        "srt_file": "out.srt",
    }


def render(folder_data):
    from django.template.loader import render_to_string

    return render_to_string(
        "transcriptions/_segments_table.html",
        {"folder_data": folder_data},
    )
