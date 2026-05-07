"""Merge Whisper word timestamps with diarization segments."""

from __future__ import annotations

from typing import Any


def merge_words(
    diarization_segments: list[dict[str, Any]],
    words: list[dict[str, Any]],
    gap_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Assign ASR words to speakers, then group them into readable segments."""
    if not diarization_segments or not words:
        return []

    ordered_diarization = sorted(diarization_segments, key=lambda item: (item["start"], item["end"]))
    assigned_words: list[dict[str, Any]] = []

    for word in words:
        text = str(word.get("text", "")).strip()
        start = float(word.get("start", 0.0) or 0.0)
        end = float(word.get("end", start) or start)
        if not text:
            continue

        speaker = _pick_speaker(start, end, ordered_diarization)
        assigned_words.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text,
        })

    return _group_assigned_words(assigned_words, gap_threshold=gap_threshold)


def _pick_speaker(start: float, end: float, diarization_segments: list[dict[str, Any]]) -> str:
    best_speaker = "UNKNOWN"
    best_overlap = -1.0
    midpoint = (start + end) / 2.0

    for segment in diarization_segments:
        overlap = _overlap(start, end, float(segment["start"]), float(segment["end"]))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = str(segment["speaker"])

    if best_overlap > 0:
        return best_speaker

    for segment in diarization_segments:
        seg_start = float(segment["start"])
        seg_end = float(segment["end"])
        if seg_start <= midpoint <= seg_end:
            return str(segment["speaker"])

    nearest = min(
        diarization_segments,
        key=lambda segment: abs((((float(segment["start"]) + float(segment["end"])) / 2.0) - midpoint)),
    )
    return str(nearest["speaker"])


def _group_assigned_words(
    assigned_words: list[dict[str, Any]],
    gap_threshold: float,
) -> list[dict[str, Any]]:
    if not assigned_words:
        return []

    ordered_words = sorted(assigned_words, key=lambda item: (item["start"], item["end"]))
    merged = [dict(ordered_words[0])]
    for word in ordered_words[1:]:
        last = merged[-1]
        same_speaker = word["speaker"] == last["speaker"]
        small_gap = (float(word["start"]) - float(last["end"])) <= gap_threshold
        if same_speaker and small_gap:
            last["end"] = float(word["end"])
            last["text"] = _join_text(str(last["text"]), str(word["text"]))
        else:
            merged.append(dict(word))
    return merged


def _join_text(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    if right[0] in ",.;:!?)]}":
        return f"{left}{right}"
    return f"{left} {right}"


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
