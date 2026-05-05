from pathlib import Path

from pydantic import BaseModel, Field


class TranscriptionRequest(BaseModel):
    audio_path: Path
    output_dir: Path | None = None
    lang: str = "fr"
    num_speakers: int | None = None
    speaker_names: list[str] = Field(default_factory=list)
    model_size: str = "medium"
    save_intermediates: bool = True
    verbose: bool = False


class TranscriptionOutput(BaseModel):
    segments: list[dict] = Field(default_factory=list)
    speaker_map: dict[str, str] = Field(default_factory=dict)
    speakers_found: int = 0
    audio_duration_s: float = 0.0
    timings: dict[str, float] = Field(default_factory=dict)
    export_txt: str = ""
    export_srt: str = ""