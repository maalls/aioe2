"""Merge diarization segments with ASR transcriptions."""

import json
from pathlib import Path

import ffmpeg

from .asr import transcribe_file, transcribe_segment


def merge(
    wav_path: Path,
    diarization_segments: list[dict],
    lang: str,
    model_size: str = "small",
    segments_dir: Path | None = None,
    transcripts_dir: Path | None = None,
) -> list[dict]:
    """
    Transcribe each diarization segment and return merged segments:
        [{"start", "end", "speaker", "text"}, ...]

    Consecutive segments from the same speaker are grouped to avoid
    fragmented output.
    """
    grouped = _group_consecutive(diarization_segments)
    result = []

    use_segment_cache = segments_dir is not None and transcripts_dir is not None
    if use_segment_cache:
        segments_dir.mkdir(parents=True, exist_ok=True)
        transcripts_dir.mkdir(parents=True, exist_ok=True)

    for idx, seg in enumerate(grouped, start=1):
        if use_segment_cache:
            segment_path = segments_dir / f"seg_{idx:06d}.wav"
            transcript_path = transcripts_dir / f"seg_{idx:06d}.json"

            if not segment_path.exists():
                _extract_segment_audio(wav_path, segment_path, seg["start"], seg["end"])

            if transcript_path.exists():
                payload = json.loads(transcript_path.read_text(encoding="utf-8"))
                text = str(payload.get("text", "")).strip()
            else:
                text = transcribe_file(segment_path, lang=lang, model_size=model_size)
                transcript_payload = {
                    "segment_id": idx,
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"],
                    "text": text,
                }
                transcript_path.write_text(
                    json.dumps(transcript_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        else:
            text = transcribe_segment(
                wav_path,
                seg["start"],
                seg["end"],
                lang=lang,
                model_size=model_size,
            )

        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "speaker": seg["speaker"],
            "text": text,
        })
    return result


def _group_consecutive(segments: list[dict], gap_threshold: float = 0.5) -> list[dict]:
    """
    Merge adjacent segments from the same speaker separated by less than
    gap_threshold seconds.
    """
    if not segments:
        return []

    ordered = sorted(segments, key=lambda s: (s["start"], s["end"]))
    merged = [dict(ordered[0])]
    for seg in ordered[1:]:
        last = merged[-1]
        same_speaker = seg["speaker"] == last["speaker"]
        small_gap = (seg["start"] - last["end"]) < gap_threshold
        if same_speaker and small_gap:
            last["end"] = seg["end"]
        else:
            merged.append(dict(seg))
    return merged


def _extract_segment_audio(
    wav_path: Path,
    output_path: Path,
    start: float,
    end: float,
) -> None:
    """
    Extract a time range from WAV into another mono 16kHz WAV file.
    """
    safe_end = max(end, start + 0.05)
    (
        ffmpeg
        .input(str(wav_path), ss=start, to=safe_end)
        .output(str(output_path), ac=1, ar=16000, acodec="pcm_s16le")
        .overwrite_output()
        .run(quiet=True)
    )
