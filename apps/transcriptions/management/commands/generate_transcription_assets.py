from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from transcriber.media_assets import find_audio_source_for_folder, generate_preview_assets


class Command(BaseCommand):
    help = "Generate preview media assets (mp3/mp4/vtt) for existing transcription output folders"

    def add_arguments(self, parser):
        parser.add_argument("--folder", default="", help="Specific folder under var/output")

    def handle(self, *args, **options):
        output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
        if not output_root.exists():
            self.stdout.write(self.style.WARNING(f"Output root does not exist: {output_root}"))
            return

        target_folder = options.get("folder", "").strip()
        folders = [output_root / target_folder] if target_folder else sorted(
            [p for p in output_root.iterdir() if p.is_dir()]
        )

        generated_count = 0
        scanned_count = 0

        for folder in folders:
            if not folder.exists() or not folder.is_dir():
                self.stdout.write(self.style.WARNING(f"Skipping missing folder: {folder.name}"))
                continue

            scanned_count += 1
            srt_files = sorted(folder.glob("*.srt"))
            if not srt_files:
                self.stdout.write(self.style.WARNING(f"[{folder.name}] no SRT found; skipped"))
                continue

            srt_path = srt_files[0]
            stem = srt_path.stem
            audio_source = find_audio_source_for_folder(folder, stem)
            if not audio_source:
                self.stdout.write(self.style.WARNING(f"[{folder.name}] no audio found; skipped"))
                continue

            assets = generate_preview_assets(
                output_dir=folder,
                stem=stem,
                input_audio_path=audio_source,
                srt_path=srt_path,
            )

            if assets:
                generated_count += 1
                self.stdout.write(self.style.SUCCESS(f"[{folder.name}] generated: {assets}"))
            else:
                self.stdout.write(self.style.WARNING(f"[{folder.name}] generation failed"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Asset generation complete: {generated_count}/{scanned_count} folders"
            )
        )
