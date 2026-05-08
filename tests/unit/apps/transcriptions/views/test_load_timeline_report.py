import json

from apps.transcriptions import views


def test_prefers_edited_json_when_present(folder_path, sample_timeline_deep_json):
    edited = {
        "chapters": [
            {
                "title": "Edited timeline",
                "start": 0.0,
                "end": 10.0,
                "summary": "",
                "analysis": {"sub_topics": []},
            }
        ]
    }
    edited_path = folder_path / "edited.json"
    edited_path.write_text(json.dumps(edited, indent=2), encoding="utf-8")

    path, data = views._load_timeline_report(folder_path)

    assert path == edited_path
    assert data["chapters"][0]["title"] == "Edited timeline"


def test_falls_back_to_timeline_deep(folder_path, sample_timeline_deep_json):
    path, data = views._load_timeline_report(folder_path)

    assert path == sample_timeline_deep_json
    assert data["chapters"][0]["title"] == "Intro"


def test_falls_back_to_timeline_json(folder_path, sample_timeline_json):
    path, data = views._load_timeline_report(folder_path)

    assert path == sample_timeline_json
    assert data["chapters"][0]["title"] == "Fallback"


def test_returns_empty_when_no_valid_timeline(folder_path):
    (folder_path / "broken.timeline.deep.json").write_text("{bad json", encoding="utf-8")

    path, data = views._load_timeline_report(folder_path)

    assert path is None
    assert data == {}
