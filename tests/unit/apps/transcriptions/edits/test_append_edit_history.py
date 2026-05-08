import json
from apps.transcriptions.edits import append_edit_history


def test_creates_file(tmp_folder):
    op = {
        "id": "op_001", "type": "edit_segment_text", "created_at": "2026-05-08T12:00:00Z",
        "before": {"segment_key": "abc", "text": "old"},
        "after":  {"segment_key": "abc", "text": "new"},
    }
    append_edit_history(tmp_folder, op)
    assert (tmp_folder / "segment_edits_history.json").exists()


def test_accumulates(tmp_folder):
    op1 = {"id": "op_001", "type": "edit_segment_text",
           "created_at": "2026-05-08T12:00:00Z", "before": {}, "after": {}}
    op2 = {"id": "op_002", "type": "rename_speaker",
           "created_at": "2026-05-08T12:01:00Z", "before": {}, "after": {}}
    append_edit_history(tmp_folder, op1)
    append_edit_history(tmp_folder, op2)
    with open(tmp_folder / "segment_edits_history.json") as f:
        history = json.load(f)
    assert len(history) == 2
    assert history[0]["id"] == "op_001"
    assert history[1]["id"] == "op_002"
