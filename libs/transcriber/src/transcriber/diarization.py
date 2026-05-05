"""Speaker diarization using pyannote.audio."""

from pathlib import Path
from typing import Optional

from .config import get_device, get_hf_token


def diarize(wav_path: Path, num_speakers: Optional[int] = None) -> list[dict]:
    """
    Run speaker diarization on a WAV file.

    Returns a list of segments:
        [{"start": float, "end": float, "speaker": "SPEAKER_00"}, ...]
    """
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=get_hf_token(),
    )

    device = get_device()
    # pyannote supports "cpu" and "cuda"; MPS falls back to CPU for stability
    import torch
    torch_device = torch.device("cpu" if device == "mps" else device)
    pipeline.to(torch_device)

    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers

    output = pipeline(str(wav_path), **kwargs)
    # pyannote >= 3.3 returns a DiarizeOutput wrapper; extract the Annotation
    annotation = output.speaker_diarization if hasattr(output, "speaker_diarization") else output

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "speaker": speaker,
        })

    return segments
