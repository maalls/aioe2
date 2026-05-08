"""
Edit-state helpers for transcription corrections.

Pure functions operate on state dicts and return new dicts (no mutation).
I/O helpers read/write edited.json and segment_edits_history.json.
"""

import copy
import hashlib
import json
import os
from pathlib import Path

EDITED_JSON_FILENAME = "edited.json"
HISTORY_JSON_FILENAME = "segment_edits_history.json"


# ── segment key ───────────────────────────────────────────────────────────────

def segment_key(segment: dict) -> str:
    raw = "|".join([
        str(segment.get("start", "")),
        str(segment.get("end", "")),
        str(segment.get("speaker", "")),
        str(segment.get("text", "")),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# ── state initialisation ──────────────────────────────────────────────────────

def build_edited_state(segments_data: dict, timeline_data: dict) -> dict:
    return {
        "segments": copy.deepcopy(segments_data.get("segments", [])),
        "speaker_map": copy.deepcopy(segments_data.get("speaker_map", {})),
        "chapters": copy.deepcopy(timeline_data.get("chapters", [])),
    }


# ── file I/O ──────────────────────────────────────────────────────────────────

def read_edited_state(folder_path: Path) -> dict | None:
    path = folder_path / EDITED_JSON_FILENAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def write_edited_state(folder_path: Path, state: dict) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    path = folder_path / EDITED_JSON_FILENAME
    tmp_path = folder_path / f"{EDITED_JSON_FILENAME}.tmp"
    tmp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, path)


def append_edit_history(folder_path: Path, operation: dict) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    path = folder_path / HISTORY_JSON_FILENAME

    history: list[dict]
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = []
        history = loaded if isinstance(loaded, list) else []
    else:
        history = []

    history.append(copy.deepcopy(operation))

    tmp_path = folder_path / f"{HISTORY_JSON_FILENAME}.tmp"
    tmp_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, path)


# ── pure state transformers ───────────────────────────────────────────────────

def apply_edit_segment_text(state: dict, seg_key: str, new_text: str) -> dict:
    updated = copy.deepcopy(state)
    for segment in updated.get("segments", []):
        if segment_key(segment) == seg_key:
            segment["text"] = new_text
            return updated
    raise KeyError(f"Unknown segment key: {seg_key}")


def apply_rename_speaker(state: dict, speaker_id: str, new_label: str) -> dict:
    updated = copy.deepcopy(state)
    speaker_map = updated.get("speaker_map", {})
    if speaker_id not in speaker_map:
        raise KeyError(f"Unknown speaker id: {speaker_id}")
    speaker_map[speaker_id] = new_label
    return updated


def apply_rename_topic(state: dict, topic_index: int, new_title: str) -> dict:
    updated = copy.deepcopy(state)
    chapters = updated.get("chapters", [])
    idx = topic_index - 1
    if idx < 0 or idx >= len(chapters):
        raise IndexError(f"Invalid topic index: {topic_index}")
    chapters[idx]["title"] = new_title
    return updated


def apply_rename_subtopic(
    state: dict, topic_index: int, subtopic_index: int, new_title: str
) -> dict:
    updated = copy.deepcopy(state)
    chapters = updated.get("chapters", [])

    topic_idx = topic_index - 1
    if topic_idx < 0 or topic_idx >= len(chapters):
        raise IndexError(f"Invalid topic index: {topic_index}")

    analysis = chapters[topic_idx].get("analysis", {})
    sub_topics = analysis.get("sub_topics", []) if isinstance(analysis, dict) else []
    sub_idx = subtopic_index - 1
    if sub_idx < 0 or sub_idx >= len(sub_topics):
        raise IndexError(f"Invalid subtopic index: {subtopic_index}")

    sub_topics[sub_idx]["title"] = new_title
    return updated
