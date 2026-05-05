from django.core.management.base import BaseCommand

from apps.transcriptions.models import JobStatus, TranscriptionJob
from apps.transcriptions.tasks import run_transcription_task


class Command(BaseCommand):
    help = "Requeue failed transcription jobs"

    def handle(self, *args, **options):
        jobs = TranscriptionJob.objects.filter(status=JobStatus.FAILED)
        count = 0
        for job in jobs.iterator():
            run_transcription_task.delay(str(job.id))
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Requeued {count} failed jobs"))