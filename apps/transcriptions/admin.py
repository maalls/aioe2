from django.contrib import admin

from .models import TranscriptionJob, TranscriptionResult


@admin.register(TranscriptionJob)
class TranscriptionJobAdmin(admin.ModelAdmin):
	list_display = ("id", "audio_file", "status", "lang", "model_size", "created_at")
	list_filter = ("status", "lang", "model_size")
	search_fields = ("id", "audio_file")


@admin.register(TranscriptionResult)
class TranscriptionResultAdmin(admin.ModelAdmin):
	list_display = ("job", "speakers_found", "audio_duration_s")
