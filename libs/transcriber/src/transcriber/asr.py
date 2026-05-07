"""ASR transcription using faster-whisper."""

from pathlib import Path

from faster_whisper import WhisperModel

from .config import get_device

_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str) -> WhisperModel:
    if model_size not in _model_cache:
        device = get_device()
        # faster-whisper uses "cpu" or "cuda"; for MPS fall back to cpu
        fw_device = "cpu" if device == "mps" else device
        compute_type = "int8" if fw_device == "cpu" else "float16"
        _model_cache[model_size] = WhisperModel(
            model_size,
            device=fw_device,
            compute_type=compute_type,
        )
    return _model_cache[model_size]


def transcribe_segment(
    wav_path: Path,
    start: float,
    end: float,
    lang: str,
    model_size: str = "small",
) -> str:
    """
    Transcribe a time-bounded segment from a WAV file.
    Returns the transcribed text (empty string if silent).
    """
    model = _get_model(model_size)
    segments, _ = model.transcribe(
        str(wav_path),
        language=lang,
        clip_timestamps=f"{start},{end}",
        word_timestamps=False,
    )
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe_file(
    audio_path: Path,
    lang: str,
    model_size: str = "small",
) -> str:
    """
    Transcribe an audio file and return the transcribed text.
    """
    model = _get_model(model_size)
    segments, _ = model.transcribe(
        str(audio_path),
        language=lang,
        word_timestamps=False,
    )
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe_file_with_word_timestamps(
    audio_path: Path,
    lang: str,
    model_size: str = "small",
) -> list[dict]:
    """Transcribe an audio file and return word-level timestamps when available."""
    model = _get_model(model_size)
    segments, _ = model.transcribe(
        str(audio_path),
        language=lang,
        word_timestamps=True,
    )

    words: list[dict] = []
    for segment in segments:
        segment_words = getattr(segment, "words", None) or []
        if segment_words:
            for word in segment_words:
                text = str(getattr(word, "word", "")).strip()
                if not text:
                    continue
                word_start = float(getattr(word, "start", segment.start) or segment.start)
                word_end = float(getattr(word, "end", segment.end) or segment.end)
                words.append({
                    "start": round(word_start, 3),
                    "end": round(word_end, 3),
                    "text": text,
                    "probability": float(getattr(word, "probability", 0.0) or 0.0),
                })
            continue

        text = segment.text.strip()
        if not text:
            continue
        words.append({
            "start": round(float(segment.start), 3),
            "end": round(float(segment.end), 3),
            "text": text,
            "probability": 0.0,
        })

    return words
