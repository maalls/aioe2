"""Export transcription results to TXT, SRT and JSON formats."""

import json
from pathlib import Path


def to_json(result: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def to_txt(segments: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for seg in segments:
        start = _fmt_time(seg["start"])
        end = _fmt_time(seg["end"])
        lines.append(f"[{start} - {end}] {seg['speaker']}: {seg['text']}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def to_srt(segments: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for i, seg in enumerate(segments, start=1):
        start = _fmt_srt_time(seg["start"])
        end = _fmt_srt_time(seg["end"])
        speaker = seg["speaker"]
        text = seg["text"]
        blocks.append(f"{i}\n{start} --> {end}\n{speaker}: {text}")
    output_path.write_text("\n\n".join(blocks), encoding="utf-8")


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
