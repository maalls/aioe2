from rest_framework import serializers

from .models import TranscriptionJob, TranscriptionResult


class TranscriptionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptionResult
        fields = (
            "segments",
            "speaker_map",
            "speakers_found",
            "audio_duration_s",
            "timings",
            "export_txt",
            "export_srt",
        )


class TranscriptionJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptionJob
        fields = (
            "id",
            "project",
            "audio_file",
            "lang",
            "num_speakers",
            "speaker_names",
            "model_size",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")

    def validate_speaker_names(self, value):
        return [str(name).strip() for name in value if str(name).strip()]


class TranscriptionJobDetailSerializer(serializers.ModelSerializer):
    result = TranscriptionResultSerializer(read_only=True)

    class Meta:
        model = TranscriptionJob
        fields = (
            "id",
            "project",
            "created_by",
            "audio_file",
            "lang",
            "num_speakers",
            "speaker_names",
            "model_size",
            "status",
            "error_message",
            "created_at",
            "completed_at",
            "result",
        )
