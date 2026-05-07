from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from infrastructure.llm.openai_compatible_client import OpenAICompatibleClient
from services.transcription_report.service import TranscriptionTimelineService


class Command(BaseCommand):
    help = "Generate a chapter timeline from a diarized transcription JSON using an LLM"

    def add_arguments(self, parser):
        parser.add_argument("--input-json", required=True)
        parser.add_argument("--output-json", default="")
        parser.add_argument("--base-url", default=settings.REPORT_LLM_BASE_URL)
        parser.add_argument("--model", default=settings.REPORT_LLM_MODEL)
        parser.add_argument("--api-key", default=settings.REPORT_LLM_API_KEY)
        parser.add_argument(
            "--deep",
            action="store_true",
            default=False,
            help="Also run per-chapter deep analysis (sub-topics, Q&A, decisions). "
                 "Output: <stem>.timeline.deep.json",
        )

    def handle(self, *args, **options):
        input_json = Path(options["input_json"]).resolve()
        if not input_json.exists():
            self.stdout.write(self.style.ERROR(f"Input file not found: {input_json}"))
            return

        output_json = Path(options["output_json"]).resolve() if options["output_json"] else None

        base_url = str(options["base_url"] or "").strip()
        model = str(options["model"] or "").strip()
        if not base_url or not model:
            self.stdout.write(
                self.style.ERROR(
                    "Timeline generation failed: LLM configuration is required. "
                    "Provide REPORT_LLM_BASE_URL and REPORT_LLM_MODEL in .env, "
                    "or pass --base-url and --model."
                )
            )
            return

        llm_client = OpenAICompatibleClient(
            base_url=base_url,
            model=model,
            api_key=options["api_key"],
        )
        service = TranscriptionTimelineService(
            llm_client=llm_client,
            max_prompt_chars=settings.REPORT_TIMELINE_MAX_PROMPT_CHARS,
        )

        deep = options["deep"]
        try:
            if deep:
                report = service.run_deep(input_json_path=input_json, output_json_path=output_json)
                suffix = ".timeline.deep.json"
            else:
                report = service.run(input_json_path=input_json, output_json_path=output_json)
                suffix = ".timeline.json"
        except Exception as exc:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f"Timeline generation failed: {exc}"))
            return

        output_path = output_json or input_json.with_name(f"{input_json.stem}{suffix}")
        label = "Deep timeline" if deep else "Timeline"
        self.stdout.write(
            self.style.SUCCESS(
                f"{label} generated: {output_path} ({report.chapter_count} chapters)"
            )
        )
