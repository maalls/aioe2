import json

from apps.transcriptions.edits import write_edited_state
from .conftest import SOURCE_SEGMENTS, SOURCE_TIMELINE


def test_creates_file(tmp_folder):
    payload = {
        "segments": SOURCE_SEGMENTS["segments"],
        "speaker_map": SOURCE_SEGMENTS["speaker_map"],
        "chapters": SOURCE_TIMELINE["chapters"],
    }
    write_edited_state(tmp_folder, payload)

    assert (tmp_folder / "edited.json").exists()


def test_writes_expected_payload(tmp_folder):
    payload = {
        "segments": SOURCE_SEGMENTS["segments"],
        "speaker_map": SOURCE_SEGMENTS["speaker_map"],
        "chapters": SOURCE_TIMELINE["chapters"],
    }
    write_edited_state(tmp_folder, payload)

    on_disk = json.loads((tmp_folder / "edited.json").read_text(encoding="utf-8"))
    assert on_disk["speaker_map"] == payload["speaker_map"]
    assert len(on_disk["segments"]) == len(payload["segments"])
    assert len(on_disk["chapters"]) == len(payload["chapters"])
