import json
from pathlib import Path

from django.core.management.base import BaseCommand

from infrastructure.llm.lm_studio_client import LMStudioClient
from services.transcription_quality.service import run_quality_check

_VALIDATIONS_BASE = Path("intermediates") / "validations"


def _cache_subdir(window: int, model: str) -> Path:
    """Stable directory name that encodes the parameters that affect LLM evaluation."""
    sanitized_model = model.replace("/", "_").replace(".", "-")
    return _VALIDATIONS_BASE / f"w{window}__{sanitized_model}"


class Command(BaseCommand):
    help = "Assess transcript quality and flag potentially bad segments"

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="Path to transcript JSON input")
        parser.add_argument(
            "--output",
            default="",
            help="Path to output report JSON (default: <input_dir>/quality_report.json)",
        )
        parser.add_argument(
            "--base-url",
            default="http://127.0.0.1:1234/v1/chat/completions",
            help="LLM chat completions URL",
        )
        parser.add_argument(
            "--model",
            default="mistralai/mistral-7b-instruct-v0.3",
            help="LLM model name",
        )
        parser.add_argument("--window", type=int, default=2, help="Context window size")
        parser.add_argument(
            "--expected-language",
            default="",
            help="Expected language (default from transcript JSON language field)",
        )
        parser.add_argument(
            "--max-segments",
            type=int,
            default=0,
            help="Limit processed segments for quick iteration",
        )
        parser.add_argument(
            "--no-cache",
            action="store_true",
            default=False,
            help="Ignore existing intermediates and re-evaluate all segments",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"]).resolve()
        if not input_path.exists():
            self.stdout.write(self.style.ERROR(f"Input file not found: {input_path}"))
            return

        output_path = self._resolve_output_path(input_path, options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        intermediates_dir = input_path.parent / _cache_subdir(options["window"], options["model"])

        if options["no_cache"] and intermediates_dir.exists():
            import shutil
            shutil.rmtree(intermediates_dir)
            self.stdout.write(self.style.WARNING(f"Cache cleared: {intermediates_dir}"))

        cached_count = len(list(intermediates_dir.glob("segment_*.json"))) if intermediates_dir.exists() else 0
        if cached_count:
            self.stdout.write(f"Resuming: {cached_count} segments already cached in {intermediates_dir}")

        max_segments = options["max_segments"] if options["max_segments"] > 0 else None
        client = LMStudioClient(base_url=options["base_url"], model=options["model"])

        report = run_quality_check(
            transcript_path=input_path,
            llm_client=client,
            context_window=options["window"],
            expected_language=options["expected_language"],
            max_segments=max_segments,
            intermediates_dir=intermediates_dir,
        )

        output_path.write_text(
            json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"Quality report written to: {output_path}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Global score: {report.global_score} | "
                f"Flagged: {report.stats.flagged_segments}/{report.stats.total_segments}"
            )
        )

    def _resolve_output_path(self, input_path: Path, raw_output: str) -> Path:
        if raw_output.strip():
            return Path(raw_output).resolve()
        return input_path.parent / "quality_report.json"
