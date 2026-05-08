"""Shared fixtures and data for transcription_edits tests."""

import pytest
from apps.transcriptions.edits import build_edited_state

SOURCE_SEGMENTS = {
    "segments": [
        {"start": 0.0,  "end": 5.0,  "speaker": "SPEAKER_00", "text": "Bonjour tout le monde"},
        {"start": 5.5,  "end": 12.0, "speaker": "SPEAKER_01", "text": "Merci d'être là"},
        {"start": 15.0, "end": 22.0, "speaker": "SPEAKER_00", "text": "On va commencer"},
        {"start": 60.0, "end": 70.0, "speaker": "SPEAKER_01", "text": "Question importante"},
    ],
    "speaker_map": {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"},
    "speakers_found": 2,
    "audio_duration_s": 75.0,
}

SOURCE_TIMELINE = {
    "source_json": "source_segments.json",
    "generated_at": "2026-05-08T12:00:00Z",
    "chapter_count": 2,
    "chapters": [
        {
            "title": "Introduction",
            "start": 0.0,
            "end": 30.0,
            "summary": "Debut de la reunion",
            "analysis": {
                "sub_topics": [
                    {"title": "Accueil",          "summary": "Salutations", "start": 0.0,  "end": 15.0},
                    {"title": "Mise en contexte", "summary": "Contexte",    "start": 15.0, "end": 30.0},
                ],
            },
        },
        {
            "title": "Discussion",
            "start": 55.0,
            "end": 75.0,
            "summary": "Questions et réponses",
            "analysis": {
                "sub_topics": [
                    {"title": "Q&A", "summary": "Questions", "start": 55.0, "end": 75.0},
                ],
            },
        },
    ],
    "warnings": [],
}


@pytest.fixture()
def tmp_folder(tmp_path):
    return tmp_path


@pytest.fixture()
def sample_state():
    return build_edited_state(SOURCE_SEGMENTS, SOURCE_TIMELINE)
