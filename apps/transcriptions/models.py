import uuid

from django.conf import settings
from django.db import models


class JobStatus(models.TextChoices):
	PENDING = "pending", "Pending"
	RUNNING = "running", "Running"
	DONE = "done", "Done"
	FAILED = "failed", "Failed"


class TranscriptionJob(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	project = models.ForeignKey(
		"projects.Project",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="transcription_jobs",
	)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="transcription_jobs",
	)
	audio_file = models.FileField(upload_to="transcriptions/input/")
	lang = models.CharField(max_length=16, default="fr")
	num_speakers = models.IntegerField(null=True, blank=True)
	speaker_names = models.JSONField(default=list, blank=True)
	model_size = models.CharField(max_length=32, default="medium")
	status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.PENDING)
	error_message = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	completed_at = models.DateTimeField(null=True, blank=True)

	def __str__(self) -> str:
		return f"{self.audio_file.name} [{self.status}]"


class TranscriptionResult(models.Model):
	job = models.OneToOneField(
		TranscriptionJob,
		on_delete=models.CASCADE,
		related_name="result",
	)
	segments = models.JSONField(default=list, blank=True)
	speaker_map = models.JSONField(default=dict, blank=True)
	speakers_found = models.IntegerField(default=0)
	audio_duration_s = models.FloatField(default=0.0)
	timings = models.JSONField(default=dict, blank=True)
	export_txt = models.TextField(blank=True)
	export_srt = models.TextField(blank=True)

	def __str__(self) -> str:
		return f"Result for {self.job_id}"
