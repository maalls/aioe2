import json

import pytest
from django.test import Client
from django.test.utils import override_settings


@pytest.mark.django_db
def test_rejects_empty_new_label(output_root, folder_name, folder_path, sample_segments_json):
    client = Client()
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        response = client.post(
            f"/transcription/edit/{folder_name}/speaker/SPEAKER_00/rename",
            data='{"label":""}',
            content_type="application/json",
        )

    assert response.status_code == 400


@pytest.mark.django_db
def test_renames_speaker_globally(output_root, folder_name, folder_path, sample_segments_json):
    client = Client()
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        response = client.post(
            f"/transcription/edit/{folder_name}/speaker/SPEAKER_00/rename",
            data='{"label":"Alison"}',
            content_type="application/json",
        )

    assert response.status_code == 200

    edited = json.loads((folder_path / "edited.json").read_text(encoding="utf-8"))
    assert edited["speaker_map"]["SPEAKER_00"] == "Alison"

    history = json.loads((folder_path / "segment_edits_history.json").read_text(encoding="utf-8"))
    assert len(history) == 1
    assert history[0]["type"] == "rename_speaker"
    assert history[0]["after"]["speaker_id"] == "SPEAKER_00"
    assert history[0]["after"]["label"] == "Alison"
