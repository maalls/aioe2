from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.transcriptions.dependencies import get_transcription2_service
from apps.transcriptions.models import JobStatus, TranscriptionJob, TranscriptionResult
from services.transcription.schemas import TranscriptionRequest
from services.transcription.youtube import download_youtube_audio


class Command(BaseCommand):
    help = "Transcribe an audio file with the ASR-first pipeline and save the result to the database"

    def add_arguments(self, parser):
        parser.add_argument("--input", default="")
        parser.add_argument("--youtube-url", default="")
        parser.add_argument("--lang", default="fr")
        parser.add_argument("--num-speakers", type=int)
        parser.add_argument("--speaker-names", default="")
        parser.add_argument("--model-size", default="medium")

    def handle(self, *args, **options):
        input_path = None
        if options["youtube_url"]:
            self.stdout.write(f"Downloading from YouTube: {options['youtube_url']}")
            input_path = download_youtube_audio(options["youtube_url"])
            self.stdout.write(self.style.SUCCESS(f"✅ Downloaded to: {input_path}"))
        elif options["input"]:
            input_path = Path(options["input"]).resolve()
        else:
            self.stdout.write(self.style.ERROR("Error: Either --input or --youtube-url is required"))
            return

        if not input_path.exists():
            self.stdout.write(self.style.ERROR(f"Error: Input file not found: {input_path}"))
            return

        speaker_names = [name.strip() for name in options["speaker_names"].split(",") if name.strip()]
        service = get_transcription2_service()

        with input_path.open("rb") as input_file:
            job = TranscriptionJob(
                lang=options["lang"],
                num_speakers=options["num_speakers"],
                speaker_names=speaker_names,
                model_size=options["model_size"],
                status=JobStatus.RUNNING,
            )
            job.audio_file.save(input_path.name, File(input_file), save=False)
            job.save()

        result = service.run(
            TranscriptionRequest(
                audio_path=job.audio_file.path,
                output_dir=service.output_root / str(job.id),
                lang=job.lang,
                num_speakers=job.num_speakers,
                speaker_names=job.speaker_names,
                model_size=job.model_size,
            )
        )
        TranscriptionResult.objects.update_or_create(
            job=job,
            defaults={
                "segments": result.segments,
                "speaker_map": result.speaker_map,
                "speakers_found": result.speakers_found,
                "audio_duration_s": result.audio_duration_s,
                "timings": result.timings,
                "export_txt": result.export_txt,
                "export_srt": result.export_srt,
            },
        )
        job.status = JobStatus.DONE
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {result.speakers_found} speakers, {len(result.segments)} segments"
            )
        )
