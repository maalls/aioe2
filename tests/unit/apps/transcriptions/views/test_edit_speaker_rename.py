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
