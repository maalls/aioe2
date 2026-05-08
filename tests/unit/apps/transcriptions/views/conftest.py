import json
from pathlib import Path

import pytest


@pytest.fixture()
def output_root(tmp_path):
    root = tmp_path / "output"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture()
def folder_name():
    return "test-folder"


@pytest.fixture()
def folder_path(output_root, folder_name):
    path = output_root / folder_name
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture()
def sample_segments_json(folder_path):
    payload = {
        "segments": [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Bonjour"},
            {"start": 2.1, "end": 4.0, "speaker": "SPEAKER_01", "text": "Salut"},
        ],
        "speaker_map": {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"},
    }
    path = folder_path / "source.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


@pytest.fixture()
def sample_timeline_deep_json(folder_path):
    payload = {
        "chapters": [
            {
                "title": "Intro",
                "start": 0.0,
                "end": 10.0,
                "summary": "",
                "analysis": {
                    "sub_topics": [
                        {"title": "Accueil", "summary": "", "start": 0.0, "end": 10.0}
                    ]
                },
            }
        ]
    }
    path = folder_path / "source.timeline.deep.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


@pytest.fixture()
def sample_timeline_json(folder_path):
    payload = {
        "chapters": [
            {
                "title": "Fallback",
                "start": 0.0,
                "end": 10.0,
                "summary": "",
                "analysis": {"sub_topics": []},
            }
        ]
    }
    path = folder_path / "source.timeline.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
