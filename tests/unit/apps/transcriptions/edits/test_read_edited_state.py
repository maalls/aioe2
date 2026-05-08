import json

from apps.transcriptions.edits import read_edited_state


def test_returns_none_when_absent(tmp_folder):
    assert read_edited_state(tmp_folder) is None


def test_reads_existing_edited_json(tmp_folder):
    payload = {
        "segments": [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00", "text": "Bonjour"}],
        "speaker_map": {"SPEAKER_00": "Alice"},
        "chapters": [],
    }
    (tmp_folder / "edited.json").write_text(json.dumps(payload), encoding="utf-8")

    loaded = read_edited_state(tmp_folder)

    assert loaded == payload
