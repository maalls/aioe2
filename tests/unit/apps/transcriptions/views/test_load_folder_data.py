import json

from django.test.utils import override_settings

from apps.transcriptions import views


def test_creates_edited_json_when_missing(output_root, folder_path, sample_segments_json, sample_timeline_deep_json):
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        data = views._load_folder_data(folder_path.name)

    assert (folder_path / "edited.json").exists()
    assert data["segments"][0]["text"] == "Bonjour"


def test_uses_edited_json_as_single_source_of_truth(
    output_root, folder_path, sample_segments_json, sample_timeline_deep_json
):
    edited_payload = {
        "segments": [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Bonjour corrige"},
            {"start": 2.1, "end": 4.0, "speaker": "SPEAKER_01", "text": "Salut"},
        ],
        "speaker_map": {"SPEAKER_00": "Alison", "SPEAKER_01": "Bob"},
        "chapters": [
            {
                "title": "Intro editee",
                "start": 0.0,
                "end": 10.0,
                "summary": "",
                "analysis": {"sub_topics": []},
            }
        ],
    }
    (folder_path / "edited.json").write_text(
        json.dumps(edited_payload, indent=2), encoding="utf-8"
    )

    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        data = views._load_folder_data(folder_path.name)

    assert data["segments"][0]["text"] == "Bonjour corrige"
    assert data["segments"][0]["speaker_label"] == "Alison"
    assert data["timeline_groups"][0]["title"] == "Intro editee"
