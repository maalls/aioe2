from django.utils import timezone
from celery import shared_task

from apps.transcriptions.dependencies import get_transcription_service
from services.transcription.schemas import TranscriptionRequest

from .models import JobStatus, TranscriptionJob, TranscriptionResult


@shared_task
def run_transcription_task(job_id: str) -> str:
    job = TranscriptionJob.objects.get(pk=job_id)
    job.status = JobStatus.RUNNING
    job.error_message = ""
    job.save(update_fields=["status", "error_message"])

    try:
        service = get_transcription_service()
        request = TranscriptionRequest(
            audio_path=job.audio_file.path,
            output_dir=service.output_root / str(job.id),
            lang=job.lang,
            num_speakers=job.num_speakers,
            speaker_names=job.speaker_names,
            model_size=job.model_size,
        )
        result = service.run(request)
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
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        raise

    return str(job.id)