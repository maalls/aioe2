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
