import hashlib
import json
from pathlib import Path

import pytest


def _segment_key(segment: dict) -> str:
    raw = "|".join(
        [
            str(segment.get("start", "")),
            str(segment.get("end", "")),
            str(segment.get("speaker", "")),
            str(segment.get("text", "")),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@pytest.fixture()
def browser_output_root(tmp_path: Path, settings) -> dict:
    output_root = tmp_path / "output"
    folder = output_root / "case-a"
    folder.mkdir(parents=True, exist_ok=True)

    segments = [
        {
            "start": 0.0,
            "end": 2.0,
            "speaker": "SPEAKER_00",
            "text": "Bonjour monde",
        },
        {
            "start": 6.0,
            "end": 8.0,
            "speaker": "SPEAKER_01",
            "text": "Deuxieme segment",
        },
    ]
    payload = {
        "segments": segments,
        "speaker_map": {
            "SPEAKER_00": "Alice",
            "SPEAKER_01": "Bob",
        },
        "speakers_found": 2,
        "audio_duration_s": 12,
    }
    (folder / "source.json").write_text(json.dumps(payload), encoding="utf-8")

    timeline = {
        "chapters": [
            {
                "title": "Intro",
                "summary": "",
                "start": 0.0,
                "end": 12.0,
                "analysis": {
                    "sub_topics": [
                        {
                            "title": "Accueil",
                            "summary": "",
                            "start": 0.0,
                            "end": 12.0,
                        }
                    ]
                },
            }
        ]
    }
    (folder / "source.timeline.deep.json").write_text(json.dumps(timeline), encoding="utf-8")

    (folder / "audio.preview.mp3").write_bytes(b"ID3")
    (folder / "run_report.json").write_text(
        json.dumps({"media_assets": {"preview_audio": "audio.preview.mp3"}}),
        encoding="utf-8",
    )

    seg0_key = _segment_key(segments[0])
    seg1_key = _segment_key(segments[1])
    (folder / "segment_bookmarks.json").write_text(
        json.dumps({"bookmarked_segment_keys": [seg0_key]}, indent=2),
        encoding="utf-8",
    )

    settings.TRANSCRIPTION_OUTPUT_ROOT = output_root

    return {
        "folder_name": "case-a",
        "folder_path": folder,
        "segment_keys": [seg0_key, seg1_key],
    }


@pytest.fixture()
def browser_page():
    pw = pytest.importorskip("playwright.sync_api")

    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                yield page
            finally:
                browser.close()
    except Exception as error:
        pytest.skip(f"Playwright unavailable in this environment: {error}")
