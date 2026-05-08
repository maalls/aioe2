import pytest
from django.test import Client
from django.test.utils import override_settings


@pytest.mark.django_db
def test_rejects_missing_title(output_root, folder_name, folder_path, sample_segments_json, sample_timeline_deep_json):
    client = Client()
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        response = client.post(
            f"/transcription/edit/{folder_name}/subtopic/1.1/rename",
            data="{}",
            content_type="application/json",
        )

    assert response.status_code == 400


@pytest.mark.django_db
def test_renames_subtopic_title(output_root, folder_name, folder_path, sample_segments_json, sample_timeline_deep_json):
    client = Client()
    with override_settings(TRANSCRIPTION_OUTPUT_ROOT=str(output_root)):
        response = client.post(
            f"/transcription/edit/{folder_name}/subtopic/1.1/rename",
            data='{"title":"Nouveau sous-topic"}',
            content_type="application/json",
        )

    assert response.status_code == 200
