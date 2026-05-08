import json

import pytest
from django.test import Client
from django.test.utils import override_settings

from apps.transcriptions.edits import segment_key


@pytest.mark.django_db
def test_rejects_missing_text_payload(output_root, folder_name, folder_path, sample_segments_json):
    client = Client()
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        response = client.post(
            f"/transcription/edit/{folder_name}/segment/df78d5c2fa35802c/text",
            data="{}",
            content_type="application/json",
        )

    assert response.status_code == 400


@pytest.mark.django_db
def test_updates_segment_text_and_persists_edited_json(output_root, folder_name, folder_path, sample_segments_json):
    first_segment = {
        "start": 0.0,
        "end": 2.0,
        "speaker": "SPEAKER_00",
        "text": "Bonjour",
    }
    seg_key = segment_key(first_segment)
    client = Client()
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        response = client.post(
            f"/transcription/edit/{folder_name}/segment/{seg_key}/text",
            data='{"text":"Bonjour corrige"}',
            content_type="application/json",
        )

    assert response.status_code == 200
    assert (folder_path / "edited.json").exists()

    edited = json.loads((folder_path / "edited.json").read_text(encoding="utf-8"))
    assert edited["segments"][0]["text"] == "Bonjour corrige"

    history_path = folder_path / "segment_edits_history.json"
    assert history_path.exists()
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(history) == 1
    assert history[0]["type"] == "edit_segment_text"
    assert history[0]["after"]["segment_key"] == seg_key
    assert history[0]["after"]["text"] == "Bonjour corrige"
