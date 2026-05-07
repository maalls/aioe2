from rest_framework import serializers

from .models import TranscriptionJob, TranscriptionResult


class TranscriptionResultSerializer(serializers.ModelSerializer):
    segments = serializers.SerializerMethodField()

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

    def get_segments(self, obj: TranscriptionResult) -> list[dict]:
        speaker_map = obj.speaker_map if isinstance(obj.speaker_map, dict) else {}
        enriched_segments: list[dict] = []
        for segment in obj.segments if isinstance(obj.segments, list) else []:
            if not isinstance(segment, dict):
                continue
            speaker_id = str(segment.get("speaker", ""))
            enriched_segments.append(
                {
                    **segment,
                    "speaker_label": speaker_map.get(speaker_id, speaker_id),
                }
            )
        return enriched_segments


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
