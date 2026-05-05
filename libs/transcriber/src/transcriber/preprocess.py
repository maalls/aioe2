"""Audio pre-processing: format conversion, normalisation, silence detection."""

from pathlib import Path

import ffmpeg


def convert_to_wav(input_path: Path, output_path: Path) -> Path:
    """
    Convert any audio file to mono 16kHz WAV.
    Returns the path to the converted file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg
        .input(str(input_path))
        .output(
            str(output_path),
            ac=1,          # mono
            ar=16000,      # 16 kHz
            acodec="pcm_s16le",
        )
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path


def get_duration(wav_path: Path) -> float:
    """Return audio duration in seconds."""
    probe = ffmpeg.probe(str(wav_path))
    return float(probe["format"]["duration"])
