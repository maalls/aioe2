import json
from pathlib import Path
from typing import Callable

from transcriber.pipeline_v2 import run_pipeline_v2

from services.transcription.schemas import TranscriptionOutput, TranscriptionRequest


PipelineFn = Callable[..., dict]


class Transcription2Service:
    def __init__(self, pipeline_fn: PipelineFn = run_pipeline_v2, output_root: Path = Path("var/output")):
        self.pipeline_fn = pipeline_fn
        self.output_root = Path(output_root)

    def run(self, request: TranscriptionRequest) -> TranscriptionOutput:
        output_dir = Path(request.output_dir) if request.output_dir else self.output_root / Path(request.audio_path).stem
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.pipeline_fn(
            input_path=Path(request.audio_path),
            output_dir=output_dir,
            lang=request.lang,
            num_speakers=request.num_speakers,
            speaker_names=request.speaker_names,
            model_size=request.model_size,
            save_intermediates=request.save_intermediates,
            verbose=request.verbose,
        )

        stem = Path(request.audio_path).stem
        run_report_path = output_dir / "run_report.json"
        run_report = (
            json.loads(run_report_path.read_text(encoding="utf-8")) if run_report_path.exists() else {}
        )

        return TranscriptionOutput(
            segments=result.get("segments", []),
            speaker_map=result.get("speaker_map", {}),
            speakers_found=int(result.get("speakers_found", 0)),
            audio_duration_s=float(result.get("audio_duration_s", 0.0)),
            timings=run_report.get("timings", {}),
            export_txt=_read_text(output_dir / f"{stem}.txt"),
            export_srt=_read_text(output_dir / f"{stem}.srt"),
        )


def run(
    request: TranscriptionRequest,
    pipeline_fn=run_pipeline_v2,
) -> TranscriptionOutput:
    return Transcription2Service(pipeline_fn=pipeline_fn).run(request)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
